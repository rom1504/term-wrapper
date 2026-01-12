"""Main entry point for terminal wrapper server."""

import uvicorn


def main():
    """Run the FastAPI server."""
    uvicorn.run(
        "term_wrapper.api:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    main()
