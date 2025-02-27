#!/usr/bin/env python3
"""Run the OpenAlex API server."""

import argparse
import uvicorn
from polus.aithena.common.logger import get_logger

logger = get_logger(__name__)


def main():
    """Run the API server."""
    parser = argparse.ArgumentParser(description="Run the OpenAlex API server")
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload on code changes"
    )
    parser.add_argument(
        "--workers", type=int, default=1, help="Number of worker processes (default: 1)"
    )

    args = parser.parse_args()

    logger.info(f"Starting OpenAlex API server at http://{args.host}:{args.port}")
    logger.info(f"API docs will be available at http://{args.host}:{args.port}/docs")

    uvicorn.run(
        "polus.aithena.jobs.getopenalex.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
