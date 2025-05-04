import logging
import os
import asyncio
from typing import List, Dict, Tuple
from dotenv import load_dotenv
from fastmcp import FastMCP
from .overseerr import Overseerr

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

initial_server_data = {
    "movie_names": tuple(),
    "tv_names": tuple(),
    "user_display_names": tuple(),
    "movie_map": {},
    "tv_map": {},
    "user_display_name_map": {}
}

async def fetch_initial_data():
    """Fetches libraries and users from Overseerr and stores them globally."""
    logger.info("Attempting to fetch initial configuration (libraries, users) from Overseerr...")
    movie_names = []
    tv_names = []
    user_display_names = []
    movie_map = {}
    tv_map = {}
    user_map = {}
    duplicate_users = []

    try:
        async with Overseerr(api_key=api_key, url=url) as client:
            try:
                radarr_servers = await client.get_radarr_servers()
                for server in radarr_servers:
                    if server.get("id") is not None and server.get("name"):
                        name = server["name"]
                        server_id = server["id"]
                        if name not in movie_map:
                            movie_names.append(name)
                            movie_map[name] = server_id
                        else:
                             logger.warning(f"Duplicate Radarr library name found: '{name}'. Skipping.")
                logger.info(f"Fetched {len(movie_names)} Radarr (Movie) libraries.")
            except Exception as e:
                logger.error(f"Failed to fetch Radarr libraries: {e}")

            try:
                sonarr_servers = await client.get_sonarr_servers()
                for server in sonarr_servers:
                     if server.get("id") is not None and server.get("name"):
                        name = server["name"]
                        server_id = server["id"]
                        if name not in tv_map:
                            tv_names.append(name)
                            tv_map[name] = server_id
                        else:
                            logger.warning(f"Duplicate Sonarr library name found: '{name}'. Skipping.")
                logger.info(f"Fetched {len(tv_names)} Sonarr (TV) libraries.")
            except Exception as e:
                logger.error(f"Failed to fetch Sonarr libraries: {e}")

            logger.info("Fetching users...")
            all_users_raw = []
            take = 50
            skip = 0
            page = 1
            total_pages = 1
            while page <= total_pages:
                try:
                    response = await client.get_users(take=take, skip=skip)
                    page_info = response.get("pageInfo", {})
                    results = response.get("results", [])
                    all_users_raw.extend(results)
                    total_pages = page_info.get("pages", 1)
                    page += 1
                    skip = (page - 1) * take
                except Exception as e:
                    logger.error(f"Failed to fetch users (page {page}): {e}")
                    break

            logger.info(f"Fetched {len(all_users_raw)} raw user entries.")
            for user in all_users_raw:
                user_id = user.get("id")
                display_name = user.get("displayName")
                if user_id is not None and display_name:
                    if display_name in user_map:
                        if display_name not in duplicate_users:
                             duplicate_users.append(display_name)
                        logger.warning(f"Duplicate user displayName found: '{display_name}'. This name cannot be used reliably in tools.")
                        if display_name in user_display_names:
                            user_display_names.remove(display_name)
                        if display_name in user_map:
                            del user_map[display_name]
                    elif display_name not in duplicate_users:
                        user_display_names.append(display_name)
                        user_map[display_name] = user_id
                else:
                    missing = []
                    if user_id is None: missing.append("ID")
                    if display_name is None: missing.append("displayName")
                    logger.warning(f"User entry missing {', '.join(missing)}: {user}")

            if duplicate_users:
                 logger.warning(f"The following user displayNames have duplicates and cannot be used for requests: {list(set(duplicate_users))}")
            logger.info(f"Processed {len(user_display_names)} unique, usable user display names.")

    except Exception as e:
        logger.error(f"Failed to connect to Overseerr to fetch initial data: {e}")

    initial_server_data["movie_names"] = tuple(sorted(movie_names))
    initial_server_data["tv_names"] = tuple(sorted(tv_names))
    initial_server_data["user_display_names"] = tuple(sorted(user_display_names))
    initial_server_data["movie_map"] = movie_map
    initial_server_data["tv_map"] = tv_map
    initial_server_data["user_display_name_map"] = user_map

try:
    asyncio.run(fetch_initial_data())
except Exception as e:
     logger.error(f"Error running initial data fetch: {e}")


app = FastMCP(name="overseerr-mcp-server", title="Overseerr MCP Server (fastmcp)")

from . import tools

def main():
    logger.info("Starting Overseerr MCP server using fastmcp...")
    logger.info(f"Movie libraries available for requests: {initial_server_data['movie_names']}")
    logger.info(f"TV libraries available for requests: {initial_server_data['tv_names']}")
    logger.info(f"User display names available for requests: {initial_server_data['user_display_names']}")
    app.run(transport='stdio')
    logger.info("Overseerr MCP server stopped.")
