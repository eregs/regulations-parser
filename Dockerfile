FROM python:3.5-alpine

COPY ["regparser", "/app/src/regparser/"]
COPY ["interpparser", "/app/src/interpparser/"]
COPY ["requirements.txt", "setup.py", "manage.py", "/app/src/"]
VOLUME ["/app/cache", "/app/output"]

WORKDIR /app/src/
RUN apk add --update libxslt libxml2-dev libxslt-dev musl-dev gcc git \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del --purge libxml2-dev libxslt-dev musl-dev gcc \
    && rm -rf /var/cache/apk/*

ENV PYTHONUNBUFFERED="1" \
    DATABASE_URL="sqlite:////app/cache/db.sqlite" \
    EREGS_CACHE_DIR="/app/cache" \
    EREGS_OUTPUT_DIR="/app/output"

ENTRYPOINT ["eregs"]
