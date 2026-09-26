FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend \
    YOUTUBARR_CONFIG_DIR=/config \
    YOUTUBARR_LIBRARY_DIR=/library \
    YOUTUBARR_CACHE_DIR=/cache \
    YOUTUBARR_VIRTUAL_MOUNT=/mnt/youtubarr \
    YOUTUBARR_HOST=0.0.0.0 \
    YOUTUBARR_PORT=8788

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg fuse3 libfuse2 util-linux curl ca-certificates tini \
    && rm -rf /var/lib/apt/lists/* \
    && printf 'user_allow_other\n' >> /etc/fuse.conf

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt
COPY backend /app/backend

RUN mkdir -p /config /library /cache /mnt/youtubarr
EXPOSE 8788
HEALTHCHECK --interval=30s --timeout=8s --start-period=25s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8788/api/bootstrap >/dev/null || exit 1
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python","-m","youtubarr.runtime"]
