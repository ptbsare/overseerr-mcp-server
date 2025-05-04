import os
import json
from typing import Any, List, Dict, Optional, Sequence, Literal, Union
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from .server import app
from .overseerr import Overseerr

load_dotenv()

# --- Configuration Loading ---
api_key = os.getenv("OVERSEERR_API_KEY", "")
url = os.getenv("OVERSEERR_URL", "")

if not api_key or not url:
    raise ValueError("OVERSEERR_API_KEY and OVERSEERR_URL environment variables are required")

# --- Library Mapping ---
DEFAULT_LIBRARY_MAP = {0: "Default Movie Library", 1: "Default TV Library"}
library_map_str = os.getenv("LIBRARY_MAP")
library_map: Dict[int, str] = {}
library_name_to_id_map: Dict[str, int] = {}

if library_map_str:
    try:
        parsed_map = json.loads(library_map_str)
        if isinstance(parsed_map, dict):
            # Validate keys are integers (or strings convertible to integers) and values are strings
            validated_map = {}
            temp_name_to_id = {}
            valid = True
            for k, v in parsed_map.items():
                try:
                    server_id = int(k)
                    if not isinstance(v, str):
                        print(f"Warning: Invalid value type for key {k} in LIBRARY_MAP. Expected string, got {type(v)}. Skipping.")
                        valid = False
                        continue
                    if v in temp_name_to_id:
                         print(f"Warning: Duplicate library name '{v}' in LIBRARY_MAP. Skipping entry for key {k}.")
                         valid = False
                         continue
                    validated_map[server_id] = v
                    temp_name_to_id[v] = server_id
                except (ValueError, TypeError):
                    print(f"Warning: Invalid key '{k}' in LIBRARY_MAP. Keys must be integers. Skipping.")
                    valid = False
            if valid and validated_map:
                 library_map = validated_map
                 library_name_to_id_map = temp_name_to_id
            else:
                 print("Warning: LIBRARY_MAP environment variable is invalid or empty after validation. Using default map.")
                 library_map = DEFAULT_LIBRARY_MAP
                 library_name_to_id_map = {v: k for k, v in library_map.items()}
        else:
            print("Warning: LIBRARY_MAP environment variable is not a valid JSON dictionary. Using default map.")
            library_map = DEFAULT_LIBRARY_MAP
            library_name_to_id_map = {v: k for k, v in library_map.items()}
    except json.JSONDecodeError:
        print("Warning: Could not decode LIBRARY_MAP environment variable as JSON. Using default map.")
        library_map = DEFAULT_LIBRARY_MAP
        library_name_to_id_map = {v: k for k, v in library_map.items()}
else:
    print("Info: LIBRARY_MAP environment variable not set. Using default map.")
    library_map = DEFAULT_LIBRARY_MAP
    library_name_to_id_map = {v: k for k, v in library_map.items()}

# Ensure default movie/tv libraries exist if map is empty or missing defaults
default_movie_name = DEFAULT_LIBRARY_MAP[0]
default_tv_name = DEFAULT_LIBRARY_MAP[1]
if 0 not in library_map:
    library_map[0] = default_movie_name
    if default_movie_name not in library_name_to_id_map: # Avoid overwriting if name exists with different ID
        library_name_to_id_map[default_movie_name] = 0
if 1 not in library_map:
     library_map[1] = default_tv_name
     if default_tv_name not in library_name_to_id_map: # Avoid overwriting
        library_name_to_id_map[default_tv_name] = 1


VALID_LIBRARY_NAMES = tuple(library_name_to_id_map.keys())
if not VALID_LIBRARY_NAMES: # Fallback if everything failed somehow
    VALID_LIBRARY_NAMES = (default_movie_name, default_tv_name)
    library_name_to_id_map = {default_movie_name: 0, default_tv_name: 1}
    library_map = {0: default_movie_name, 1: default_tv_name}


# --- Media Status Mapping ---
MEDIA_STATUS_MAPPING = {
    1: "UNKNOWN",
    2: "PENDING",
    3: "PROCESSING",
    4: "PARTIALLY_AVAILABLE",
    5: "AVAILABLE"
}

@app.tool()
async def overseerr_status():
    """Get the status of the Overseerr server. No arguments required."""
    async with Overseerr(api_key=api_key, url=url) as client:
        data = await client.get_status()

    if "version" in data:
        status_response = f"\n---\nOverseerr is available and these are the status data:\n"
        status_response += "\n- " + "\n- ".join([f"{key}: {val}" for key, val in data.items()])
    else:
        status_response = f"\n---\nOverseerr is not available and below is the request error: \n"
        status_response += "\n- " + "\n- ".join([f"{key}: {val}" for key, val in data.items()])

    return status_response


@app.tool()
async def overseerr_movie_requests(
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    take: Optional[int] = 7,
    skip: Optional[int] = 0
):
    """Get a paginated list of movie requests that satisfy the filter arguments.

    Args:
        status (Optional[str]): Filter by media availability status (e.g., "pending", "available", "approved"). Valid values: "all", "approved", "available", "pending", "processing", "unavailable", "failed". Defaults to all if omitted or invalid.
        start_date (Optional[str]): Filter for requests created on or after this date, formatted as 'YYYY-MM-DDTHH:MM:SS.mmmZ'.
        take (Optional[int]): The number of results to return (page size). Defaults to 7.
        skip (Optional[int]): The number of results to skip (for pagination). Defaults to 0.
    """
    take = max(0, take if take is not None else 7)
    skip = max(0, skip if skip is not None else 0)

    async with Overseerr(api_key=api_key, url=url) as client:
        valid_statuses = ["all", "approved", "available", "pending", "processing", "unavailable", "failed"]
        if status and status not in valid_statuses:
            status = None

        all_results = []
        api_params: Dict[str, Any] = {"take": take, "skip": skip}
        if status and status != "all":
            api_params["filter"] = status

        try:
            response = await client.get_requests(api_params)
            results = response.get("results", [])

            for result in results:
                media_info = result.get("media", {})
                if media_info and not media_info.get("tvdbId"):
                    created_at = result.get("createdAt", "")
                    if start_date and start_date > created_at:
                        continue

                    movie_id = media_info.get("tmdbId")
                    if movie_id:
                        try:
                            movie_details = await client.get_movie_details(movie_id)
                            title = movie_details.get("title", "Unknown Movie")
                        except Exception:
                             title = f"Unknown Movie (ID: {movie_id})"
                    else:
                        title = "Unknown Movie (No TMDB ID)"


                    media_status_code = media_info.get("status", 1)
                    media_availability = MEDIA_STATUS_MAPPING.get(media_status_code, "UNKNOWN")

                    formatted_result = {
                        "title": title,
                        "media_availability": media_availability,
                        "request_date": created_at
                    }
                    all_results.append(formatted_result)

        except Exception as e:
            return {"error": f"Error fetching movie requests: {str(e)}"}


    return all_results


@app.tool()
async def overseerr_tv_requests(
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    take: Optional[int] = 7,
    skip: Optional[int] = 0
):
    """Get a paginated list of TV show requests that satisfy the filter arguments.

    Args:
        status (Optional[str]): Filter by media availability status (e.g., "pending", "available", "approved"). Valid values: "all", "approved", "available", "pending", "processing", "unavailable", "failed". Defaults to all if omitted or invalid.
        start_date (Optional[str]): Filter for requests created on or after this date, formatted as 'YYYY-MM-DDTHH:MM:SS.mmmZ'.
        take (Optional[int]): The number of results to return (page size). Defaults to 7.
        skip (Optional[int]): The number of results to skip (for pagination). Defaults to 0.
    """
    take = max(0, take if take is not None else 7)
    skip = max(0, skip if skip is not None else 0)

    async with Overseerr(api_key=api_key, url=url) as client:
        valid_statuses = ["all", "approved", "available", "pending", "processing", "unavailable", "failed"]
        if status and status not in valid_statuses:
            status = None

        all_results = []
        api_params: Dict[str, Any] = {"take": take, "skip": skip}
        if status and status != "all":
            api_params["filter"] = status

        try:
            response = await client.get_requests(api_params)
            results = response.get("results", [])

            for result in results:
                media_info = result.get("media", {})
                if media_info and media_info.get("tvdbId"):
                    created_at = result.get("createdAt", "")
                    if start_date and start_date > created_at:
                        continue

                    tv_id = media_info.get("tmdbId")
                    tv_title = "Unknown TV Show"
                    seasons_data = []
                    if tv_id:
                        try:
                            tv_details = await client.get_tv_details(tv_id)
                            tv_title = tv_details.get("name", "Unknown TV Show")
                            seasons_data = tv_details.get("seasons", [])
                        except Exception:
                            tv_title = f"Unknown TV Show (ID: {tv_id})"
                            seasons_data = []
                    else:
                         tv_title = "Unknown TV Show (No TMDB ID)"


                    media_status_code = media_info.get("status", 1)
                    tv_title_availability = MEDIA_STATUS_MAPPING.get(media_status_code, "UNKNOWN")

                    requested_seasons = {s.get("seasonNumber") for s in result.get("seasons", [])}

                    for season_summary in seasons_data:
                        season_number = season_summary.get("seasonNumber")

                        if season_number is None or season_number == 0:
                            continue
                        if requested_seasons and season_number not in requested_seasons:
                            continue


                        season_str = f"S{season_number:02d}"
                        episode_details_list = []
                        tv_season_availability = tv_title_availability

                        try:

                            season_details = await client.get_season_details(tv_id, season_number)


                            for episode in season_details.get("episodes", []):
                                episode_number = episode.get("episodeNumber", 0)
                                episode_details_list.append({
                                    "episode_number": f"{episode_number:02d}",
                                    "episode_name": episode.get("name", f"Episode {episode_number}")

                                })
                        except Exception:

                            episode_details_list = [{"error": f"Could not fetch details for {season_str}"}]


                        formatted_result = {
                            "tv_title": tv_title,
                            "tv_title_availability": tv_title_availability,
                            "tv_season": season_str,
                            "tv_season_availability": tv_season_availability,
                            "tv_episodes": episode_details_list,
                            "request_date": created_at
                        }
                        all_results.append(formatted_result)

        except Exception as e:
            return {"error": f"Error fetching TV requests: {str(e)}"}

    return all_results


# --- Pydantic Models for Request Tools ---

class BaseRequestArgs(BaseModel):
    tmdb_id: int = Field(..., description="The The Movie Database (TMDB) ID of the media to request.")
    user_id: Optional[int] = Field(None, description="Overseerr user ID to make the request as. Overrides environment variable if provided. Defaults to REQUEST_USER_ID env var or 1.")

class MovieRequestArgs(BaseRequestArgs):
    library_name: Literal[VALID_LIBRARY_NAMES] = Field( # type: ignore
        default=library_map.get(0, next(iter(VALID_LIBRARY_NAMES))), # Default to serverId 0 name or first available
        description=f"The target library for the movie request. Choose from: {', '.join(VALID_LIBRARY_NAMES)}"
    )

class TvRequestArgs(BaseRequestArgs):
    seasons: Optional[List[int]] = Field(None, description="List of season numbers to request. If omitted or empty, all seasons will be requested.")
    library_name: Literal[VALID_LIBRARY_NAMES] = Field( # type: ignore
        default=library_map.get(1, next(iter(VALID_LIBRARY_NAMES))), # Default to serverId 1 name or first available
        description=f"The target library for the TV show request. Choose from: {', '.join(VALID_LIBRARY_NAMES)}"
    )

# --- Tool Definitions ---

@app.tool()
async def overseerr_request_movie(args: MovieRequestArgs):
    """Submit a movie request to Overseerr, specifying the target library."""
    try:
        server_id = library_name_to_id_map.get(args.library_name)
        # We should always find the name due to Literal validation, but check defensively
        if server_id is None:
             return {"error": f"Internal error: Could not map library name '{args.library_name}' to a server ID."}

        async with Overseerr(api_key=api_key, url=url) as client:
            result = await client.request_movie(
                tmdb_id=args.tmdb_id,
                user_id=args.user_id,
                server_id=server_id
            )
        return result
    except ValidationError as e:
         return {"error": f"Invalid arguments: {e}"}
    except Exception as e:
        return {"error": f"Error submitting movie request: {str(e)}"}


@app.tool()
async def overseerr_request_tv(args: TvRequestArgs):
    """Submit a TV show request to Overseerr, specifying seasons and the target library."""
    try:
        server_id = library_name_to_id_map.get(args.library_name)
        if server_id is None:
             return {"error": f"Internal error: Could not map library name '{args.library_name}' to a server ID."}

        async with Overseerr(api_key=api_key, url=url) as client:
            result = await client.request_tv(
                tmdb_id=args.tmdb_id,
                seasons=args.seasons,
                user_id=args.user_id,
                server_id=server_id
            )
        return result
    except ValidationError as e:
         return {"error": f"Invalid arguments: {e}"}
    except Exception as e:
        return {"error": f"Error submitting TV show request: {str(e)}"}


@app.tool()
async def overseerr_search_media(query: str, page: int = 1):
    """Search for movies and TV shows available on Overseerr.

    Args:
        query (str): The search term (e.g., movie or TV show title).
        page (int): The page number for pagination (default is 1).
    """
    response_text = ""
    try:
        async with Overseerr(api_key=api_key, url=url) as client:
            results_data = await client.search_media(query=query, page=page)

        formatted_results = []
        for item in results_data.get("results", []):
            media_type = item.get("mediaType", "unknown")
            tmdb_id = item.get("id")
            title = "Unknown Title"
            year = ""
            overview = item.get("overview", "No overview available.")
            original_language = item.get("originalLanguage", "N/A")

            details_lines = [f"  Original Language: {original_language}"]

            if media_type == "movie":
                title = item.get("title", "Unknown Movie")
                original_title = item.get("originalTitle", title)
                release_date = item.get("releaseDate")
                if release_date:
                    year = f"({release_date.split('-')[0]})"
                details_lines.insert(0, f"  Original Title: {original_title}")

            elif media_type == "tv":
                title = item.get("name", "Unknown TV Show")
                original_name = item.get("originalName", title)
                origin_countries = ", ".join(item.get("originCountry", []))
                first_air_date = item.get("firstAirDate")
                if first_air_date:
                    year = f"({first_air_date.split('-')[0]})"
                details_lines.insert(0, f"  Original Name: {original_name}")
                details_lines.insert(1, f"  Origin Country: {origin_countries or 'N/A'}")

            formatted_item = {
                "type": media_type.capitalize(),
                "title": title,
                "year": year.strip('()') if year else None,
                "tmdb_id": tmdb_id,
                "original_language": original_language,
                "overview": overview,
                "original_title": original_title if media_type == "movie" else None,
                "original_name": original_name if media_type == "tv" else None,
                "origin_country": origin_countries if media_type == "tv" else None,
            }
            formatted_results.append({k: v for k, v in formatted_item.items() if v is not None})


        if not formatted_results:
            return {"message": f"No results found for query '{query}' on page {page}."}
        else:
            return formatted_results

    except Exception as e:
        return {"error": f"Error searching media: {str(e)}"}
