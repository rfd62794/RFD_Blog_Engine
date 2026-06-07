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

if __name__ == "__main__":
    cli()
