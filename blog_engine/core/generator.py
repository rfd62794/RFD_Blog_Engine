"""
blog_engine/core/generator.py

Internal blog post generation using model router.
"""

from pathlib import Path
from typing import Optional
import asyncio

from blog_engine.infra.model_router import ModelRouter
from blog_engine.infra.db_manager import DBManager
from blog_engine.infra.logger import get_logger
from blog_engine.core.inventory import InventoryManager
from blog_engine.core.draft_manager import DraftManager

RFD_CONTENT_FRAME_PROMPT = """
You are writing a blog post for Robert Floyd Dugger (rfditservices.com).

Voice: Direct, honest, technical. No filler. No motivational language.
Frame: MOMENT → SURPRISE → STRUGGLE → LESSON → NEXT
- MOMENT: One specific scene. Where, what, what happened. 2-3 sentences. Present tense.
- SURPRISE: What was unexpected. 1-2 sentences.
- STRUGGLE: The actual friction — technical, logistical, or cognitive. 2-3 sentences.
- LESSON: What is now known that wasn't before. One sentence. Distilled.
- NEXT: What changes as a result. 1-2 sentences. Forward motion.

Post details:
Title: {title}
Category: {category}
Notes: {notes}
Tags: {tags}

Additional context from past sessions:
{context}

Write the full blog post using the RFD Content Frame. 400-600 words.
No headers. No bullet points. Prose only. Authentic voice.
Do not use: "genuinely", "fascinating", "dive into", "delve", "certainly".
End with a single forward-looking sentence.
"""


class PostGenerator:
    def __init__(
        self,
        db: DBManager,
        inventory: InventoryManager,
        draft_manager: DraftManager,
        model_router: ModelRouter
    ):
        self.db = db
        self.inventory = inventory
        self.draft_manager = draft_manager
        self.router = model_router
        self.logger = get_logger(__name__)

    async def generate(
        self,
        post_id: str,
        model: Optional[str] = None,
        override_frame: bool = False
    ) -> dict:
        """
        Full generation pipeline:
        1. Load post context from inventory
        2. Load frame slots from SQLite post_context (if exist)
        3. Construct prompt
        4. Route to model
        5. Save as draft via DraftManager
        6. Return draft dict

        Raises FileNotFoundError if post_id not in inventory.
        Raises RuntimeError if all models fail.
        Raises ValueError if draft already exists and override_frame=False.
        """
        self.logger.info("generation.start", post_id=post_id, model=model or "auto")
        
        # Load inventory context
        try:
            inventory_context = self.inventory.get_context_for_generation(post_id)
        except KeyError:
            raise FileNotFoundError(f"Post not found in inventory: {post_id}")
        
        # Load frame context from SQLite
        frame_context = self._extract_frame_context(post_id)
        
        # Build prompt
        prompt = self._build_prompt(inventory_context, frame_context)
        
        # Route to model
        try:
            response = self.router.generate(prompt, model=model)
        except Exception as e:
            self.logger.error("generation.failed", post_id=post_id, error=str(e))
            raise RuntimeError(f"Model generation failed: {e}")
        
        # Check for empty response
        if not response or not response.strip():
            raise RuntimeError("Generation produced empty content")
        
        # Parse response into draft content
        title = inventory_context["title"]
        content = response.strip()
        excerpt = content[:200] + "..." if len(content) > 200 else content
        
        # Save draft via DraftManager
        try:
            self.draft_manager.create_draft(
                post_id=post_id,
                title=title,
                content=content,
                excerpt=excerpt,
                tags=inventory_context["tags"],
                categories=[inventory_context["category"]] if inventory_context["category"] else [],
                tags_source="auto",
                categories_source="auto",
                generation_source="internal"
            )
        except ValueError as e:
            if "already exists" in str(e) and not override_frame:
                raise ValueError(f"Draft already exists for {post_id}. Use override_frame=True to regenerate.")
            raise
        
        self.logger.info("generation.success", post_id=post_id, model=model or "auto")
        
        return {
            "post_id": post_id,
            "title": title,
            "content": content,
            "excerpt": excerpt,
            "tags": inventory_context["tags"],
            "categories": [inventory_context["category"]] if inventory_context["category"] else [],
            "tags_source": "auto",
            "categories_source": "auto",
            "generation_source": "internal"
        }

    def _build_prompt(
        self,
        inventory_context: dict,
        frame_context: Optional[dict] = None
    ) -> str:
        """
        Constructs the full generation prompt.
        Merges inventory notes with SQLite frame slots if available.
        Returns formatted prompt string.
        """
        # Build context string from frame slots
        if frame_context:
            context_str = f"""
Frame slots:
- Moment: {frame_context.get('frame_moment', '')}
- Surprise: {frame_context.get('frame_surprise', '')}
- Struggle: {frame_context.get('frame_struggle', '')}
- Lesson: {frame_context.get('frame_lesson', '')}
- Next: {frame_context.get('frame_next', '')}
"""
        else:
            context_str = "No frame context available."
        
        prompt = RFD_CONTENT_FRAME_PROMPT.format(
            title=inventory_context["title"],
            category=inventory_context["category"],
            notes=inventory_context["notes"],
            tags=", ".join(inventory_context["tags"]),
            context=context_str
        )
        
        return prompt

    def _extract_frame_context(self, post_id: str) -> Optional[dict]:
        """
        Loads post_context from SQLite for post_id.
        Returns dict of frame slots or None if no context exists.
        """
        row = self.db.fetchone(
            "SELECT frame_moment, frame_surprise, frame_struggle, frame_lesson, frame_next "
            "FROM post_context WHERE post_id = ?",
            (post_id,)
        )
        
        if not row:
            return None
        
        return {
            "frame_moment": row["frame_moment"] or "",
            "frame_surprise": row["frame_surprise"] or "",
            "frame_struggle": row["frame_struggle"] or "",
            "frame_lesson": row["frame_lesson"] or "",
            "frame_next": row["frame_next"] or ""
        }
