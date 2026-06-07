"""
blog_engine/infra/model_router.py

Model router for rfd-blog-engine.
Simplified from PrivyBot's infra/model_router.py for standalone use.
Routes LLM calls: Groq → Gemini → OpenRouter → Ollama.
"""

import logging
import os
from typing import Callable

logger = logging.getLogger("blog_engine.model_router")


def _get_groq_client():
    """Get Groq client if credentials available."""
    if not os.getenv("GROQ_API_KEY"):
        return None
    try:
        from groq import Groq
        return Groq(api_key=os.getenv("GROQ_API_KEY"))
    except ImportError:
        logger.warning("groq package not installed")
        return None


def _get_gemini_client():
    """Get Gemini client if credentials available."""
    if not os.getenv("GEMINI_API_KEY"):
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        return genai
    except ImportError:
        logger.warning("google-generativeai package not installed")
        return None


def _get_openrouter_client():
    """Get OpenRouter client if credentials available."""
    if not os.getenv("OPENROUTER_API_KEY"):
        return None
    try:
        from openai import OpenAI
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
    except ImportError:
        logger.warning("openai package not installed")
        return None


def _get_ollama_client():
    """Get Ollama client (local, no credentials needed)."""
    try:
        from openai import OpenAI
        return OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"  # Ollama doesn't need real key
        )
    except ImportError:
        logger.warning("openai package not installed for Ollama")
        return None


def _call_groq(model: str, prompt: str, **kwargs) -> str:
    """Call Groq API."""
    client = _get_groq_client()
    if not client:
        raise RuntimeError("Groq client not available")
    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        **kwargs
    )
    return response.choices[0].message.content


def _call_gemini(model: str, prompt: str, **kwargs) -> str:
    """Call Gemini API."""
    genai = _get_gemini_client()
    if not genai:
        raise RuntimeError("Gemini client not available")
    
    model_obj = genai.GenerativeModel(model)
    response = model_obj.generate_content(prompt)
    return response.text


def _call_openrouter(model: str, prompt: str, **kwargs) -> str:
    """Call OpenRouter API."""
    client = _get_openrouter_client()
    if not client:
        raise RuntimeError("OpenRouter client not available")
    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        **kwargs
    )
    return response.choices[0].message.content


def _call_ollama(model: str, prompt: str, **kwargs) -> str:
    """Call Ollama (local)."""
    client = _get_ollama_client()
    if not client:
        raise RuntimeError("Ollama client not available")
    
    # Default model if not specified
    if not model:
        model = os.getenv("OLLAMA_MODEL", "llama3")
    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        **kwargs
    )
    return response.choices[0].message.content


def route(role: str, prompt: str, **kwargs) -> dict:
    """
    Route an LLM call to the best available model.

    Tries models in order:
    1. Groq (free, fast)
    2. Gemini Direct
    3. OpenRouter
    4. Ollama (local, last resort)

    Returns dict with keys: result (str), model_used (str), provider (str)
    Raises RuntimeError if all models fail.
    """
    # Model hierarchy for each role
    role_models = {
        "generation": [
            ("groq", "llama3-70b-8192"),
            ("gemini", "gemini-1.5-flash"),
            ("openrouter", "anthropic/claude-3-haiku"),
            ("ollama", "llama3"),
        ],
        "default": [
            ("groq", "llama3-8b-8192"),
            ("gemini", "gemini-1.5-flash"),
            ("openrouter", "meta-llama/llama-3-8b-instruct"),
            ("ollama", "llama3"),
        ],
    }
    
    candidates = role_models.get(role, role_models["default"])
    
    last_error = None
    for provider, model_id in candidates:
        try:
            if provider == "groq":
                result = _call_groq(model_id, prompt, **kwargs)
            elif provider == "gemini":
                result = _call_gemini(model_id, prompt, **kwargs)
            elif provider == "openrouter":
                result = _call_openrouter(model_id, prompt, **kwargs)
            elif provider == "ollama":
                result = _call_ollama(model_id, prompt, **kwargs)
            else:
                raise ValueError(f"Unknown provider: {provider}")
            
            logger.info(f"Role '{role}' served by {provider}/{model_id}")
            return {
                "result": result,
                "model_used": model_id,
                "provider": provider
            }
        
        except Exception as e:
            logger.warning(f"Model {provider}/{model_id} failed for role {role}: {e}")
            last_error = e
            continue
    
    raise RuntimeError(
        f"All models failed for role '{role}'. Last error: {last_error}"
    )
