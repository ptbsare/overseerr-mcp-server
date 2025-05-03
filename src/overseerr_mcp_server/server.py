import logging
import os
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastmcp-overseerr")

api_key = os.getenv("OVERSEERR_API_KEY")
url = os.getenv("OVERSEERR_URL")

if not api_key or not url:
    cwd = os.getcwd()
    error_msg = f"OVERSEERR_API_KEY and OVERSEERR_URL environment variables are required. Working directory: {cwd}"
    logger.error(error_msg)
    raise ValueError(error_msg)

app = FastMCP(name="overseerr-mcp-server", title="Overseerr MCP Server (fastmcp)")

from . import tools

def main():
    logger.info("Starting Overseerr MCP server using fastmcp...")
    app.run(transport='stdio')
    logger.info("Overseerr MCP server stopped.")
