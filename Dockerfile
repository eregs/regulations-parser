FROM python:2.7-alpine

COPY ["regparser", "/app/src/regparser/"]
COPY ["settings.py", "eregs.py", "requirements.txt", "setup.py", "/app/src/"]
VOLUME ["/app/cache", "/app/output"]

WORKDIR /app/src/
RUN apk add --update libxslt libxml2-dev libxslt-dev musl-dev gcc git \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del --purge libxml2-dev libxslt-dev musl-dev gcc \
    && rm -rf /var/cache/apk/* \
    && ./manage.py migrate

ENV PYTHONUNBUFFERED="1" \
    EREGS_CACHE_DIR="/app/cache" \
    EREGS_OUTPUT_DIR="/app/output"

ENTRYPOINT ["eregs"]
