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

if __name__ == "__main__":
    cli()
