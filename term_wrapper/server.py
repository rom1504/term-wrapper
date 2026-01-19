"""Server entry point for terminal wrapper."""

import argparse
import uvicorn


def main():
    """Run the FastAPI server."""
    parser = argparse.ArgumentParser(description="Terminal Wrapper Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--log-level", default="info", help="Log level")
    args = parser.parse_args()

    print(f"Starting server on {args.host}:{args.port}")
    print(f"Open http://{args.host}:{args.port}/ in your browser")

    uvicorn.run(
        "term_wrapper.api:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
