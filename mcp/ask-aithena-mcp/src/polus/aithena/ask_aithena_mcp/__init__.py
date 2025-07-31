from .server import mcp

def main():
    """Main entry point for the ask-aithena-mcp server."""
    mcp.run(transport="http", port=8000)

if __name__ == "__main__":
    main()
