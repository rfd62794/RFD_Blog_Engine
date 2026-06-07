"""
blog_engine/server.py

FastMCP server for rfd-blog-engine.
Exposes all tools to Claude Desktop via stdio transport.
"""

import os
# Suppress FastMCP startup banner to avoid polluting MCP JSON stream
os.environ["FASTMCP_LOG_LEVEL"] = "ERROR"
os.environ["FASTMCP_QUIET"] = "1"
os.environ["FASTMCP_NO_BANNER"] = "1"

from pathlib import Path
from dotenv import load_dotenv

# Load .env with explicit path before anything else
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from fastmcp import FastMCP
from blog_engine.infra.db_manager import DBManager
from blog_engine.tools.generate_tools import register_generate_tools
from blog_engine.tools.draft_tools import register_draft_tools
from blog_engine.tools.publish_tools import register_publish_tools

db = DBManager()
db.initialize_schema()

mcp = FastMCP("rfd-blog-engine")

register_generate_tools(mcp)
register_draft_tools(mcp)
register_publish_tools(mcp)

if __name__ == "__main__":
    mcp.run()
