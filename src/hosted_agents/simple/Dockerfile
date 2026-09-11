# Foundry hosted agents run linux/amd64. On Apple Silicon build with:
#   docker build --platform linux/amd64 -t demo-agent .
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first so code edits don't bust the pip layer
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Precompile to cut cold-start time; app code compiled strictly so syntax errors fail the build
RUN python -m compileall -q "$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')" || true; \
    python -m compileall -q .

# Hosted agent contract: HTTP on 8088, GET /readiness, POST /responses (served by the host)
EXPOSE 8088

# Loads langgraph.json -> main.py:create_graph and serves the Responses protocol
CMD ["python", "-m", "langchain_azure_ai.agents.hosting.run", "--protocol", "responses"]
