FROM python:3.13-slim

WORKDIR /app

# Install uv and dependencies
RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    export PATH="$HOME/.local/bin:$PATH"

COPY . /app

# Install Python dependencies
RUN /root/.local/bin/uv sync

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
