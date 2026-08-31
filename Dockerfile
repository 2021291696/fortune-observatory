FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install --no-cache-dir uv \
    && useradd --system --uid 10001 --home-dir /srv --shell /usr/sbin/nologin fortune

WORKDIR /srv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY apps/api ./apps/api
COPY data/rules ./data/rules
COPY data/ephemeris ./data/ephemeris
COPY apps/observatory/dist ./apps/observatory/dist

RUN chown -R fortune:fortune /srv

ENV PYTHONPATH=/srv/src:/srv/apps/api \
    FORTUNE_ALLOWED_HOSTS="127.0.0.1,localhost"

USER fortune
EXPOSE 8080

CMD ["/srv/.venv/bin/python", "-m", "uvicorn", "serve:serve", "--host", "0.0.0.0", "--port", "8080"]
