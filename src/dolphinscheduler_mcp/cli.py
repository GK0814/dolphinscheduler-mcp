"""Command-line interface for DolphinScheduler MCP."""

import argparse
import sys
import os

from .server import run_server


def main() -> int:
    """Parse command-line arguments and run the server."""
    parser = argparse.ArgumentParser(
        description="DolphinScheduler Model Context Protocol (MCP) Server"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("DOLPHINSCHEDULER_MCP_HOST", "0.0.0.0"),
        help="Host to bind the server (default: 0.0.0.0 or DOLPHINSCHEDULER_MCP_HOST env var)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("DOLPHINSCHEDULER_MCP_PORT", "8089")),
        help="Port to bind the server (default: 8089 or DOLPHINSCHEDULER_MCP_PORT env var)",
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse", "streamable-http"],
        default=os.environ.get("DOLPHINSCHEDULER_MCP_TRANSPORT", "stdio"),
        help="MCP transport to use (default: stdio or DOLPHINSCHEDULER_MCP_TRANSPORT env var)",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=os.environ.get("DOLPHINSCHEDULER_MCP_PATH", "/mcp"),
        help="HTTP path for streamable-http transport (default: /mcp)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="DolphinScheduler API URL (default: DOLPHINSCHEDULER_API_URL env var)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="DolphinScheduler API key (default: DOLPHINSCHEDULER_API_KEY env var)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.environ.get("DOLPHINSCHEDULER_MCP_LOG_LEVEL", "INFO"),
        help="Logging level (default: INFO or DOLPHINSCHEDULER_MCP_LOG_LEVEL env var)",
    )

    args = parser.parse_args()

    # Set environment variables if provided through command-line args
    if args.api_url:
        os.environ["DOLPHINSCHEDULER_API_URL"] = args.api_url
    if args.api_key:
        os.environ["DOLPHINSCHEDULER_API_KEY"] = args.api_key
    
    # Check if API URL and key are set
    if "DOLPHINSCHEDULER_API_URL" not in os.environ:
        print(
            "Warning: DOLPHINSCHEDULER_API_URL environment variable is not set.",
            file=sys.stderr,
        )
        print("Using default: http://localhost:12345/dolphinscheduler", file=sys.stderr)
    
    if "DOLPHINSCHEDULER_API_KEY" not in os.environ:
        print(
            "Warning: DOLPHINSCHEDULER_API_KEY environment variable is not set.",
            file=sys.stderr,
        )
        print("Authentication to the DolphinScheduler API may fail.", file=sys.stderr)
    
    # Set logging level
    os.environ["DOLPHINSCHEDULER_MCP_LOG_LEVEL"] = args.log_level

    # Run the server
    try:
        run_server(
            host=args.host,
            port=args.port,
            transport=args.transport,
            path=args.path,
        )
        return 0
    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
