import httpx
import os
from typing import Any, List, Dict, Optional

class Overseerr:
    def __init__(
            self,
            api_key: str,
            url: str,
            timeout: tuple = (5, 30)
        ):
        self.api_key = api_key
        self.url = url.rstrip('/')
        self.timeout = httpx.Timeout(timeout[0], connect=timeout[1])
        self._client: Optional[httpx.AsyncClient] = None
        request_user_id_str = os.getenv("REQUEST_USER_ID", "1")
        try:
            self.default_request_user_id = int(request_user_id_str)
        except ValueError:
            self.default_request_user_id = 1

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _get_headers(self) -> dict:
        return {
            'Accept': 'application/json',
            'X-Api-Key': self.api_key
        }

    async def _safe_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        client = await self._get_client()
        try:
            response = await client.request(method, endpoint, **kwargs)
            response.raise_for_status()

            if response.status_code in [200, 201, 204]:
                if response.status_code == 204 or not response.content:
                    if method.upper() in ["POST", "PUT", "DELETE", "PATCH"]:
                         return {"status": "success", "message": f"Operation {method} on {endpoint} successful."}
                    else:
                         return {}
                try:
                    return response.json()
                except ValueError:
                    raise Exception(f"Invalid JSON received from {endpoint}: {response.text}")

            return response.json()

        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                message = error_data.get('message', '<unknown error message>')
            except ValueError:
                message = e.response.text or '<no error details>'
            raise Exception(f"Overseerr API Error {e.response.status_code} on {method} {endpoint}: {message}") from e
        except httpx.RequestError as e:
            raise Exception(f"Network request failed for {method} {endpoint}: {str(e)}") from e
        except Exception as e:
            raise Exception(f"An unexpected error occurred during the request to {endpoint}: {str(e)}") from e


    async def get_status(self) -> Dict[str, Any]:
        return await self._safe_request("GET", "/api/v1/status")

    async def get_movie_details(self, movie_id: int) -> Dict[str, Any]:
        return await self._safe_request("GET", f"/api/v1/movie/{movie_id}")

    async def get_tv_details(self, tv_id: int) -> Dict[str, Any]:
        return await self._safe_request("GET", f"/api/v1/tv/{tv_id}")

    async def get_season_details(self, tv_id: int, season_id: int) -> Dict[str, Any]:
        return await self._safe_request("GET", f"/api/v1/tv/{tv_id}/season/{season_id}")

    async def request_movie(self, tmdb_id: int, user_id: Optional[int] = None, server_id: Optional[int] = None) -> Dict[str, Any]:
        requesting_user_id = user_id if user_id is not None else self.default_request_user_id
        data = {
            "mediaType": "movie",
            "mediaId": tmdb_id,
            "userId": requesting_user_id
        }
        if server_id is not None:
            data["serverId"] = server_id
        return await self._safe_request("POST", "/api/v1/request", json=data)

    async def request_tv(self, tmdb_id: int, seasons: Optional[List[int]] = None, user_id: Optional[int] = None, server_id: Optional[int] = None) -> Dict[str, Any]:
        requesting_user_id = user_id if user_id is not None else self.default_request_user_id
        data = {
            "mediaType": "tv",
            "mediaId": tmdb_id,
            "seasons": seasons if seasons else [-1], # Use -1 for all seasons as per Overseerr API convention
            "userId": requesting_user_id
        }
        if server_id is not None:
            data["serverId"] = server_id
        return await self._safe_request("POST", "/api/v1/request", json=data)

    async def get_requests(self, params: Dict[str, Any] = {}) -> Dict[str, Any]:
        processed_params = {k: v for k, v in params.items() if v is not None}
        return await self._safe_request("GET", "/api/v1/request", params=processed_params)

    async def search_media(self, query: str, page: int = 1) -> Dict[str, Any]:
        params = {
            "query": query,
            "page": page
        }
        return await self._safe_request("GET", "/api/v1/search", params=params)

    async def __aenter__(self):
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
