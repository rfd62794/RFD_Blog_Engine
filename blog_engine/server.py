"""
blog_engine/server.py

FastMCP server for rfd-blog-engine.
Exposes all tools to Claude Desktop via stdio transport.
"""

from fastmcp import FastMCP
from blog_engine.tools.generate_tools import register_generate_tools
from blog_engine.tools.draft_tools import register_draft_tools
from blog_engine.tools.publish_tools import register_publish_tools

mcp = FastMCP("rfd-blog-engine")

register_generate_tools(mcp)
register_draft_tools(mcp)
register_publish_tools(mcp)

if __name__ == "__main__":
    mcp.run()
