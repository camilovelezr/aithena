FROM ghcr.io/astral-sh/uv:python3.11-bookworm

# environment variables
ENV AITHENA_LOG_LEVEL="DEBUG"
ENV EXEC_DIR="/opt/executables"

WORKDIR ${EXEC_DIR}

# Set environment variables to avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Copy the repository into the container
COPY agents/ask-aithena-agent ${EXEC_DIR}/aithena/agents/ask-aithena-agent/
COPY common ${EXEC_DIR}/aithena/common

# Install the tool
# RUN pip3 install "${EXEC_DIR}/aithena/agents/ask-aithena-agent"
WORKDIR ${EXEC_DIR}/aithena/agents/ask-aithena-agent

# Install
RUN uv sync

# Use the CLI command instead of direct uvicorn
ENTRYPOINT ["uv", "run", "ask-aithena", "serve", "--log-level", "DEBUG", "--host", "0.0.0.0", "--port", "8000"]
