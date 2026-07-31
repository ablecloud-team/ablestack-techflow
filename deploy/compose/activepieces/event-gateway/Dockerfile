FROM python:3.12.11-alpine3.22

WORKDIR /opt/techflow/event-gateway
COPY gateway.py /opt/techflow/event-gateway/gateway.py

USER 65532:65532
EXPOSE 8081

CMD ["python", "/opt/techflow/event-gateway/gateway.py"]
