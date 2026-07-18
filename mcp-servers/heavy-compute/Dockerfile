# Heavy Compute MCP image for Synthex.
# Provides: sympy_solve, profile_script, etl_validate (with pandas/pyarrow), docker_run.
FROM python:3.12-slim
WORKDIR /app
COPY server.py .
RUN pip install --no-cache-dir mcp sympy pandas pyarrow
RUN groupadd -r synthex && useradd -r -g synthex synthex && chown -R synthex:synthex /app
USER synthex
ENTRYPOINT ["python", "server.py"]
