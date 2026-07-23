FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation and use copy link mode for uv in Docker
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy configuration and lock files
COPY pyproject.toml uv.lock ./

# Install dependencies first
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code and files required for packaging
COPY README.md ./
COPY agent.py ./
COPY analyzers/ ./analyzers/
COPY models/ ./models/
COPY services/ ./services/

# Sync the project itself to create the project-guardian console script
RUN uv sync --frozen --no-dev

# Add virtualenv bin to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Configure a non-root user for security
RUN useradd -u 10001 -m guardian && \
    chown -R guardian:guardian /app

USER guardian

# Default command runs the diagnostics check
CMD ["project-guardian", "doctor"]
