"""Server entry point for terminal wrapper."""

import argparse
import uvicorn


def main():
    """Run the FastAPI server."""
    parser = argparse.ArgumentParser(description="Terminal Wrapper Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1 for security)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--log-level", default="info", help="Log level")
    args = parser.parse_args()

    # Display localhost in URL for better UX
    display_host = "localhost" if args.host in ("127.0.0.1", "localhost") else args.host
    print(f"Starting server on {args.host}:{args.port}")
    print(f"Open http://{display_host}:{args.port}/ in your browser")

    uvicorn.run(
        "term_wrapper.api:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
