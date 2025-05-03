# FastMCP server for Overseerr

FastMCP server to interact with the Overseerr API for movie and TV show requests management, built using the `fastmcp` library.

Project Repository: [https://github.com/ptbsare/overseerr-mcp-server](https://github.com/ptbsare/overseerr-mcp-server)

## Components

### Tools

The server implements the following tools to interact with Overseerr:

-   `overseerr_status`: Get the status of the Overseerr server.
-   `overseerr_movie_requests`: Get a paginated list of movie requests that satisfy the filter arguments. Accepts optional `take` (default 7) and `skip` (default 0) parameters for pagination.
-   `overseerr_tv_requests`: Get a paginated list of TV show requests that satisfy the filter arguments. Accepts optional `take` (default 7) and `skip` (default 0) parameters for pagination.
-   `overseerr_request_movie`: Submit a movie request using its TMDB ID. Accepts an optional `user_id` parameter to specify the Overseerr user making the request (priority: parameter > `REQUEST_USER_ID` env var > default 1).
-   `overseerr_request_tv`: Submit a TV show request using its TMDB ID, optionally specifying seasons. Accepts an optional `user_id` parameter (same priority as movie requests).
-   `overseerr_search_media`: Search for movies and TV shows available on Overseerr.

### Example prompts

It's good to first instruct your AI assistant (e.g., Claude) to use the Overseerr tools. Then it can call the appropriate tool when needed.

Try prompts like these:

-   Get the status of our Overseerr server.
-   Show me all the movie requests that are currently pending.
-   List all TV show requests from the last month that are now available.
-   What movies have been requested but are not available yet?
-   What TV shows have recently become available in our library?
-   Search for the movie "Dune: Part Two" on Overseerr.
-   Request the movie with TMDB ID 693134.
-   Request seasons 1 and 2 for the TV show with TMDB ID 1396.

## Configuration

### Overseerr API Key & URL

You need to provide your Overseerr API key and URL. There are two ways to configure this:

1.  **Add to server config (preferred for clients like Claude Desktop):**

    Modify your client's MCP server configuration (e.g., `claude_desktop_config.json`). Since the package is not published, you need to run it from the source directory using `uv`.

    ```json
    {
      "mcpServers": {
        "overseerr-mcp": {
          "command": "uv", // Use uv command runner
          "args": [
             "run",
             "--directory",
             "/path/to/overseerr-mcp-server", // Replace with the actual path to the cloned repo
             "overseerr-mcp-server" // The script name defined in pyproject.toml
           ],
          "env": {
            "OVERSEERR_API_KEY": "<your_api_key_here>",
            "OVERSEERR_URL": "<your_overseerr_url>"
"REQUEST_USER_ID": "1" // Optional: Overseerr user ID to make requests as (defaults to 1)
          }
        }
      }
    }
    ```
    *Replace `/path/to/overseerr-mcp-server` with the actual path where you cloned the repository.*

2.  **Create a `.env` file:**

    Create a `.env` file in the root directory of the cloned repository (`/path/to/overseerr-mcp-server`) with the following content:

    ```dotenv
    OVERSEERR_API_KEY=your_api_key_here
    REQUEST_USER_ID=1 # Optional: Overseerr user ID to make requests as (defaults to 1)
    OVERSEERR_URL=your_overseerr_url_here
    ```
    The server will load these variables when run from the project directory.

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
uv venv # Create virtual environment
source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
uv pip install -e . # Install in editable mode
```

### Running the Server (Development)

You can run the server directly from the project directory using `uv`:

```bash
# Make sure your virtual environment is active
# Ensure .env file exists or environment variables are set
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
