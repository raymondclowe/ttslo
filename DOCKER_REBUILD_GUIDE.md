# Docker Image Rebuild Guide

## Quick Reference

When you update source code and need to rebuild the Docker image for `instance2`:

```bash
cd ~/ttslo
docker build --no-cache -t docker_ttslo_instance2 -f docker/Dockerfile .
cd /opt/ttslo/docker
docker-compose down
docker-compose up -d
```

## Architecture Overview

- **Primary instance**: Runs directly via systemd from `/opt/ttslo/` (no Docker)
- **Secondary instance** (instance2): Runs in Docker container
  - Image: `docker_ttslo_instance2`
  - Data directory: `/opt/ttslo/instance2/` (mounted as `/config` in container)
  - Port: 8002
  - Config: `/opt/ttslo/docker/docker-compose.yml`

## Common Issues and Solutions

### Issue 1: "docker/entrypoint.sh: not found" during build

**Symptoms:**
```
ERROR: failed to compute cache key: "/docker/entrypoint.sh": not found
```

**Root Cause:**
`.dockerignore` was excluding the `docker/` directory, preventing `docker/entrypoint.sh` from being included in the build context.

**Solution:**
Edit `.dockerignore` and remove these lines:
- `docker/`
- `Dockerfile`
- `.dockerignore`

Keep `docker-compose.yml` in `.dockerignore` since it's not needed in the image.

**Current correct `.dockerignore` has:**
```
# Docker
docker-compose.yml
```
(NOT excluding docker/, Dockerfile, or .dockerignore)

### Issue 2: "unrecognized arguments: --config" on container startup

**Symptoms:**
```
dashboard.py: error: unrecognized arguments: --config /config/config.csv
Container exits with code 2
```

**Root Cause:**
Mismatch between old cached `entrypoint.sh` (using `--config` argument) and new `dashboard.py` (using environment variables `TTSLO_CONFIG_FILE` instead).

**Solution:**
Rebuild with `--no-cache` flag to ensure fresh copy of all files:
```bash
docker build --no-cache -t docker_ttslo_instance2 -f docker/Dockerfile .
```

**Dead End Investigations:**
- ❌ Checking if docker-compose.yml has command override (it doesn't)
- ❌ Looking for CMD in Dockerfile (only has ENTRYPOINT)
- ❌ Checking if dashboard.py was calling itself recursively (it wasn't)

**Actual Issue:**
Docker was using a cached layer with old `entrypoint.sh` that included `--config "$CONFIG_DIR/config.csv"` argument, while new dashboard.py doesn't accept `--config`.

### Issue 3: docker-compose errors with 'ContainerConfig' KeyError

**Symptoms:**
```
KeyError: 'ContainerConfig'
ERROR: for ttslo_instance2  'ContainerConfig'
```

**Root Cause:**
Old container metadata conflicting when trying to recreate container with new image.

**Solution:**
Clean state with `docker-compose down` before bringing it back up:
```bash
cd /opt/ttslo/docker
docker-compose down
docker-compose up -d
```

If that doesn't work, manually remove the problematic container:
```bash
docker rm -f ttslo_instance2  # or use container ID
docker-compose up -d
```

## Correct Build Process

### From Dev to Production

1. **Make changes in dev** (`~/ttslo`)
   ```bash
   cd ~/ttslo
   # Edit files...
   ```

2. **Build Docker image** (from project root, not docker/ subdirectory)
   ```bash
   docker build --no-cache -t docker_ttslo_instance2 -f docker/Dockerfile .
   ```
   
   **Important:**
   - Build from project root (`.` context) so all files are available
   - Use `-f docker/Dockerfile` to specify Dockerfile location
   - Use `--no-cache` to ensure fresh build with latest code

3. **Restart container with docker-compose**
   ```bash
   cd /opt/ttslo/docker
   docker-compose down
   docker-compose up -d
   ```

4. **Verify container is running**
   ```bash
   docker ps
   docker logs ttslo_instance2
   curl http://localhost:8002/
   ```

## Environment Variables

The container gets environment variables from `/opt/ttslo/docker/docker-compose.yml`:
- `KRAKEN_API_KEY` / `KRAKEN_API_SECRET` (read-only)
- `KRAKEN_API_KEY_RW` / `KRAKEN_API_SECRET_RW` (read-write)
- `TELEGRAM_BOT_TOKEN`
- `DASHBOARD_PORT` (default: 8002)

The `entrypoint.sh` converts these into file path environment variables:
- `TTSLO_CONFIG_FILE=/config/config.csv`
- `TTSLO_STATE_FILE=/config/state.csv`
- `TTSLO_LOG_FILE=/config/logs.csv`

## File Structure

```
/opt/ttslo/                    # Production deployment
├── docker/
│   ├── docker-compose.yml     # Container config with env vars
│   └── entrypoint.sh          # Container startup script
└── instance2/                 # Data directory (mounted as /config)
    ├── config.csv
    ├── state.csv
    └── logs.csv (if exists)

~/ttslo/                       # Development source
├── .dockerignore              # MUST NOT exclude docker/ or Dockerfile
├── docker/
│   ├── Dockerfile
│   └── entrypoint.sh
├── dashboard.py
├── ttslo.py
└── ... (all source files)
```

## Debugging Tips

1. **Check what's in the built image:**
   ```bash
   docker run --rm --entrypoint cat docker_ttslo_instance2 /entrypoint.sh
   docker run --rm --entrypoint ls docker_ttslo_instance2 -la /app
   ```

2. **Test image before deploying:**
   ```bash
   docker run --rm -e DASHBOARD_PORT=8002 docker_ttslo_instance2
   ```

3. **Check container logs:**
   ```bash
   docker logs ttslo_instance2
   docker logs -f ttslo_instance2  # Follow
   ```

4. **Inspect running container:**
   ```bash
   docker exec -it ttslo_instance2 bash
   docker exec ttslo_instance2 cat /entrypoint.sh
   ```

5. **View docker-compose config:**
   ```bash
   cd /opt/ttslo/docker
   docker-compose config
   ```

## Related Files

- Main README: [README.md](README.md)
- Docker documentation: [DOCKER.md](DOCKER.md)
- Learnings/best practices: [LEARNINGS.md](LEARNINGS.md)
- Agent instructions: [AGENTS.md](AGENTS.md)
