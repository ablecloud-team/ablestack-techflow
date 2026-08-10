FROM python:3.12.11-alpine3.22@sha256:efcdfa6a6b2fd2afb9c7dfa9a5b288a6f68338b5cfdebe6b637d986067d85757

ARG TECHFLOW_GATEWAY_VERSION=0.3.0
LABEL org.opencontainers.image.title="ABLESTACK TechFlow Event Gateway" \
      org.opencontainers.image.version="${TECHFLOW_GATEWAY_VERSION}" \
      org.opencontainers.image.source="https://github.com/ablecloud-team/ablestack-techflow"

WORKDIR /opt/techflow/event-gateway
COPY gateway.py /opt/techflow/event-gateway/gateway.py

USER 65532:65532
EXPOSE 8081

CMD ["python", "/opt/techflow/event-gateway/gateway.py"]
