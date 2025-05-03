import os
from typing import Any, List, Dict, Optional, Sequence
from dotenv import load_dotenv

from .server import app
from .overseerr import Overseerr

load_dotenv()

api_key = os.getenv("OVERSEERR_API_KEY", "")
url = os.getenv("OVERSEERR_URL", "")

if not api_key or not url:
    raise ValueError("OVERSEERR_API_KEY and OVERSEERR_URL environment variables are required")

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


@app.tool()
async def overseerr_request_movie(tmdb_id: int, user_id: Optional[int] = None):
    """Submit a movie request to Overseerr using its TMDB ID.

    Args:
        tmdb_id (int): The The Movie Database (TMDB) ID of the movie to request.
        user_id (Optional[int]): Overseerr user ID to make the request as. Overrides environment variable if provided. Defaults to REQUEST_USER_ID env var or 1.
    """
    response_text = ""
    try:
        async with Overseerr(api_key=api_key, url=url) as client:
            result = await client.request_movie(tmdb_id=tmdb_id, user_id=user_id)
        return result
    except Exception as e:
        response_text = f"Error submitting movie request: {str(e)}"
        return response_text


@app.tool()
async def overseerr_request_tv(tmdb_id: int, seasons: Optional[List[int]] = None, user_id: Optional[int] = None):
    """Submit a TV show request to Overseerr using its TMDB ID. Optionally specify seasons.

    Args:
        tmdb_id (int): The The Movie Database (TMDB) ID of the TV show to request.
        seasons (Optional[List[int]]): List of season numbers to request. If omitted or empty, all seasons will be requested.
        user_id (Optional[int]): Overseerr user ID to make the request as. Overrides environment variable if provided. Defaults to REQUEST_USER_ID env var or 1.
    """
    response_text = ""
    try:
        async with Overseerr(api_key=api_key, url=url) as client:
            result = await client.request_tv(tmdb_id=tmdb_id, seasons=seasons, user_id=user_id)
        return result
    except Exception as e:
        response_text = f"Error submitting TV show request: {str(e)}"
        return response_text


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
