# Multi-stage build for terragrunt-gcp-mcp
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

# Copy source code and install the package
COPY src/ ./src/
COPY README.md CHANGELOG.md LICENSE.md ./
RUN pip install -e .

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Terragrunt
ARG TERRAGRUNT_VERSION=0.53.0
RUN curl -L "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/terragrunt_linux_amd64" -o /usr/local/bin/terragrunt \
    && chmod +x /usr/local/bin/terragrunt

# Install OpenTofu
ARG OPENTOFU_VERSION=1.6.0
RUN curl -L "https://github.com/opentofu/opentofu/releases/download/v${OPENTOFU_VERSION}/tofu_${OPENTOFU_VERSION}_linux_amd64.zip" -o tofu.zip \
    && unzip tofu.zip \
    && mv tofu /usr/local/bin/ \
    && chmod +x /usr/local/bin/tofu \
    && rm tofu.zip

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user
RUN groupadd -r terragrunt && useradd -r -g terragrunt -d /app -s /bin/bash terragrunt

# Set working directory
WORKDIR /app

# Copy configuration files
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/.terragrunt-cache \
    && chown -R terragrunt:terragrunt /app

# Switch to non-root user
USER terragrunt

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import terragrunt_gcp_mcp; print('OK')" || exit 1

# Expose port for MCP server
EXPOSE 8000

# Set default command
CMD ["terragrunt-gcp-mcp", "server"]

# Labels for metadata
LABEL org.opencontainers.image.title="Terragrunt GCP MCP Tool" \
      org.opencontainers.image.description="MCP server for Terragrunt GCP infrastructure management" \
      org.opencontainers.image.vendor="Infrastructure Team" \
      org.opencontainers.image.licenses="GPL-3.0" \
      org.opencontainers.image.source="https://github.com/yourusername/terragrunt-gcp-mcp" \
      org.opencontainers.image.documentation="https://github.com/yourusername/terragrunt-gcp-mcp#readme" 