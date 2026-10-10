"""
blog_engine/cli.py

Click CLI entry point for rfd-blog-engine.
"""

import click
import subprocess
import sys

@click.group()
def cli():
    """rfd-blog-engine — Blog post generation and publishing MCP server."""
    pass

@cli.command()
def serve():
    """Start the MCP server (stdio transport)."""
    from blog_engine.server import mcp
    mcp.run()

@cli.command()
def version():
    """Print version."""
    from blog_engine import __version__
    click.echo(f"rfd-blog-engine {__version__}")

@cli.command()
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--apply", "do_apply", is_flag=True, default=False)
@click.option("--mapping", default="data/backfill_mapping.yaml")
def backfill(dry_run, do_apply, mapping):
    """Backfill lane/category/tags/featured-image/excerpt onto existing posts."""
    if dry_run == do_apply:
        raise click.UsageError("pass exactly one of --dry-run or --apply")
    import asyncio
    from blog_engine.core.backfill import walk
    results = asyncio.run(walk(mapping, dry_run=dry_run))
    for r in results:
        click.echo(r)
    updated = sum(1 for r in results if r.get("action") == "updated")
    skipped = len(results) - updated
    if do_apply:
        all_403 = (
            updated == 0
            and skipped > 0
            and all("403" in str(r.get("error", "")) for r in results)
        )
        if all_403:
            click.echo(
                f"apply: {updated} updated, {skipped} skipped (403) - "
                "credential lacks edit_published_posts"
            )
        else:
            click.echo(f"apply: {updated} updated, {skipped} skipped")
    else:
        click.echo(f"dry-run: {len(results)} posts")

@cli.command()
@click.option("--since-days", default=2, show_default=True, type=int)
@click.option("--dry-run", is_flag=True, default=False)
def generate_daily(since_days, dry_run):
    """Scan recent repo activity, register candidates, generate drafts (free lane)."""
    import asyncio

    from blog_engine.core.source_scan import register_candidates, scan_recent_activity

    candidates = scan_recent_activity(since_days=since_days)
    if not candidates:
        # Exact string — an AgentFlow [specialists.jobs] skip_if matches on it.
        click.echo("NO_CANDIDATES")
        return

    if dry_run:
        for c in candidates:
            click.echo(f"candidate: {c['post_id']} {c['title']} ({c['source_repo']}@{c['source_ref']})")
        return

    from blog_engine.core.draft_manager import DraftManager
    from blog_engine.core.generator import PostGenerator
    from blog_engine.core.inventory import InventoryManager
    from blog_engine.infra.db_manager import DBManager

    db = DBManager()
    inventory = InventoryManager()
    generator = PostGenerator(db, inventory, DraftManager(db))

    for post_id in register_candidates(candidates, inventory):
        result = asyncio.run(generator.generate(post_id))
        click.echo(f"generated: {result['post_id']} {result['title']}")

@cli.command()
@click.argument("post_id")
def approve(post_id):
    """Approve a draft so it can be pushed to WordPress as pending. Does not publish anything."""
    from blog_engine.core.draft_manager import DraftManager
    from blog_engine.infra.db_manager import DBManager

    db = DBManager()
    draft_manager = DraftManager(db=db)
    try:
        draft = draft_manager.approve_draft(post_id, approved_by="robert")
    except ValueError as e:
        raise click.UsageError(str(e))
    click.echo(f"{draft['post_id']}: status={draft['status']} approved_at={draft['approved_at']}")

if __name__ == "__main__":
    cli()
