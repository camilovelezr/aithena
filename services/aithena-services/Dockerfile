FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Environment variables
ENV AITHENA_LOG_LEVEL="DEBUG"
ENV EXEC_DIR="/opt/executables"
WORKDIR ${EXEC_DIR}


# Copy the required directories
COPY common ${EXEC_DIR}/aithena/common
COPY services/aithena-services ${EXEC_DIR}/aithena/services/aithena-services


# Set environment variables to avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR ${EXEC_DIR}/aithena/services/aithena-services
# Install the tool using uv
RUN uv sync

# Expose the application port
EXPOSE 8000

# Run the application using the CLI
# Environment variables can be passed via docker run -e or docker-compose environment:
# Example: docker run -e POSTGRES_HOST=my-db-host -e POSTGRES_PORT=5433 ...
CMD ["uv", "run", "aithena-services", "serve", "--host", "0.0.0.0", "--port", "8000"]