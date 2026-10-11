FROM python:3.12-slim
WORKDIR /app
COPY fba_triage.py mcp_server.py ./
ENTRYPOINT ["python", "mcp_server.py"]
