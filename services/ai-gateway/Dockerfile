FROM python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/techflow-ai-gateway

COPY requirements.lock ./requirements.lock
RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --requirement requirements.lock \
    && addgroup --system --gid 10001 techflow \
    && adduser --system --uid 10001 --gid 10001 --home /nonexistent --no-create-home techflow

COPY --chown=10001:10001 app ./app
COPY --chown=10001:10001 migrations ./migrations
COPY --chown=10001:10001 scripts ./scripts
RUN chmod 0555 /opt/techflow-ai-gateway/scripts/container-entrypoint.sh \
    /opt/techflow-ai-gateway/scripts/migrate.py \
    /opt/techflow-ai-gateway/scripts/reconcile_sources.py \
    && git --version

USER 10001:10001
EXPOSE 8090
ENTRYPOINT ["/opt/techflow-ai-gateway/scripts/container-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090", "--no-access-log"]
