# FastMCP server for Overseerr

FastMCP server to interact with the Overseerr API for movie and TV show requests management, built using the `fastmcp` library.

Project Repository: [https://github.com/ptbsare/overseerr-mcp-server](https://github.com/ptbsare/overseerr-mcp-server)

## Components

### Tools

The server implements the following tools to interact with Overseerr:

-   `overseerr_status`: Get the status of the Overseerr server.
-   `overseerr_movie_requests`: Get a paginated list of movie requests. Accepts optional `status`, `start_date` (YYYY-MM-DDTHH:MM:SS.mmmZ format), `take` (default 7), and `skip` (default 0).
-   `overseerr_tv_requests`: Get a paginated list of TV show requests. Accepts optional `status`, `start_date` (YYYY-MM-DDTHH:MM:SS.mmmZ format), `take` (default 7), and `skip` (default 0).
-   `overseerr_request_movie_to_library`: Submit a movie request using its TMDB ID to a specific library, on behalf of a specific user. Requires `tmdb_id`, `library_name`, and `user_display_name`. Available library names and user display names (unique ones only) are fetched at server startup and included in the tool's argument descriptions.
-   `overseerr_request_tv_to_library`: Submit a TV show request using its TMDB ID to a specific library, on behalf of a specific user. Requires `tmdb_id`, `library_name`, and `user_display_name`. Optionally accepts `seasons` (list of integers). Available library names and user display names (unique ones only) are fetched at server startup and included in the tool's argument descriptions.
-   `overseerr_search_media`: Search for movies and TV shows available on Overseerr. Accepts `query` and optional `page` (default 1).
-   `overseerr_get_available_libraries`: Get the configured Sonarr (TV) and Radarr (Movie) server IDs and names from Overseerr.
-   `overseerr_get_users`: Get a list of all users configured in Overseerr, including their ID, username, email, displayName, etc.

### Example prompts

It's good to first instruct your AI assistant (e.g., Claude) to use the Overseerr tools. Then it can call the appropriate tool when needed.

Try prompts like these:

-   Get the status of our Overseerr server.
-   Show me the first 5 movie requests that are currently pending.
-   List all TV show requests from 2024-01-01 that are now available.
-   What movies have been requested but are not available yet?
-   What TV shows have recently become available in our library?
-   Search for the movie "Dune: Part Two" on Overseerr.
-   What movie and TV libraries are configured in Overseerr?
-   List all users in Overseerr.
-   Request the movie with TMDB ID 693134 for the user 'John Doe' in the 'Movies HD' library. (Uses `user_display_name='John Doe'`, `library_name='Movies HD'`)
-   Request seasons 1 and 2 for the TV show with TMDB ID 1396 for user 'Jane Smith' in the 'TV Shows 4K' library. (Uses `user_display_name='Jane Smith'`)

## Configuration

### Environment Variables

You need to provide your Overseerr API key and URL. There are two ways to configure this:

1.  **Add to server config (preferred for clients like Claude Desktop):**

    Modify your client's MCP server configuration (e.g., `claude_desktop_config.json`). Since the package is not published, you need to run it from the source directory using `uv`.

    ```json
    {
      "mcpServers": {
        "overseerr-mcp-server": {
          "command": "uv",
          "args": [
             "run",
             "--directory",
             "/path/to/overseerr-mcp-server", // Replace with actual path
             "overseerr-mcp-server"
           ],
          "env": {
            "OVERSEERR_API_KEY": "<your_api_key_here>",
            "OVERSEERR_URL": "<your_overseerr_url>"
          }
        }
      }
    }
    ```
    *Replace `/path/to/overseerr-mcp-server` with the actual path where you cloned the repository.*

2.  **Create a `.env` file:**

    Create a `.env` file in the root directory of the cloned repository (`/path/to/overseerr-mcp-server`) with the following content:

    ```dotenv
    # Required: Your Overseerr API Key
    OVERSEERR_API_KEY=your_api_key_here

    # Required: The URL of your Overseerr instance (e.g., http://localhost:5055)
    OVERSEERR_URL=your_overseerr_url_here
    ```

*Note: You can find the API key in the Overseerr settings under "API Keys".*

## Quickstart

### Prerequisites

-   Python >= 3.12
-   `uv` (installation instructions: [https://github.com/astral-sh/uv](https://github.com/astral-sh/uv))
-   An Overseerr instance running.
-   API Key from your Overseerr instance (Settings → API Keys).

### Installation

Clone the repository and set up the environment using `uv`:

```bash
git clone https://github.com/ptbsare/overseerr-mcp-server.git
cd overseerr-mcp-server
uv venv
source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
uv pip install -e .
```

### Running the Server (Development)

You can run the server directly from the project directory using `uv`:

```bash
# Make sure your virtual environment is active
# Ensure .env file exists or environment variables are set in config
uv run overseerr-mcp-server
```

The server will start and listen for MCP communication over stdio. Configure your MCP client (like Claude Desktop) to connect to it using the `uv run --directory ...` command as shown in the configuration section.

## Development

### Setup

Follow the installation steps using `uv pip install -e .` for an editable install.

### Dependencies

Install or sync dependencies using `uv`:

```bash
uv sync
# or
uv pip install -e .
```

### Debugging

Since MCP servers run over stdio, debugging can be challenging.

-   **MCP Inspector:** The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is highly recommended.

    Launch it pointing to your server script via `uv run`:

    ```bash
    # Make sure your virtual environment is active
    npx @modelcontextprotocol/inspector uv run --directory /path/to/overseerr-mcp-server overseerr-mcp-server
    ```
    *Replace `/path/to/overseerr-mcp-server` with the actual path.*
    Access the URL provided by the Inspector in your browser.

-   **Logging:** The server logs basic information to stdout/stderr. Check the terminal where you ran `uv run overseerr-mcp-server`. For clients like Claude Desktop, check the client's log files (e.g., `~/Library/Logs/Claude/mcp-server-overseerr-mcp.log` on macOS, but the name might vary based on your config).

## License

MIT
