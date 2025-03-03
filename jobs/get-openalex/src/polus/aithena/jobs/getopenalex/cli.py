import typer

# Add this import for the API server
from .api.run import start_server

app = typer.Typer()
s3_app = typer.Typer()
app.add_typer(s3_app, name="s3", help="S3 bucket operations")


@app.command("version")
def version():
    """Display the current version of get-openalex."""
    from . import __version__

    typer.echo(f"get-openalex version: {__version__}")


# Add the serve command to launch the API server
@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind the API server to"),
    port: int = typer.Option(8000, help="Port for the API server"),
    reload: bool = typer.Option(False, help="Enable auto-reload for development"),
):
    """Start the OpenAlex API server."""
    typer.echo(f"Starting API server at {host}:{port}")
    start_server(host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
