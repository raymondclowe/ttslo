FROM python:3.13-slim

WORKDIR /app

# Install uv, supervisor, and dependencies
RUN apt-get update && apt-get install -y curl supervisor && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    export PATH="$HOME/.local/bin:$PATH" && \
    mkdir -p /var/log/supervisor && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY . /app

# Install Python dependencies
RUN /root/.local/bin/uv sync

# Copy supervisor configuration and make scripts executable
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/run-dashboard.sh /app/docker/run-dashboard.sh
RUN chmod +x /app/docker/run-dashboard.sh

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
