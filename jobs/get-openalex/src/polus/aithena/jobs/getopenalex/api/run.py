#!/usr/bin/env python3
"""Run the OpenAlex API server."""

import typer
import uvicorn

from polus.aithena.common.logger import get_logger
from polus.aithena.jobs.getopenalex.config import API_HOST
from polus.aithena.jobs.getopenalex.config import API_PORT

logger = get_logger(__name__)

DEFAULT_API_PORT = 8000
app = typer.Typer()


def start_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
) -> None:
    """Start the FastAPI server."""
    # Use values from config or command line arguments
    host = API_HOST if host == "127.0.0.1" else host
    port = API_PORT if port == DEFAULT_API_PORT else port

    logger.info(f"Starting OpenAlex API server at http://{host}:{port}")
    logger.info(f"API docs will be available at http://{host}:{port}/docs")

    uvicorn.run(
        "polus.aithena.jobs.getopenalex.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def main(
    host: str = typer.Option("127.0.0.1", help="Host to bind the API server to"),
    port: int = typer.Option(DEFAULT_API_PORT, help="Port for the API server"),
    reload: bool = typer.Option(False, help="Enable auto-reload for development"),
) -> None:
    """Start the OpenAlex API server."""
    start_server(host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
