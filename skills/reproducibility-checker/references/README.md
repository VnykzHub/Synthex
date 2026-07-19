# Reproducibility Checker — Reference

## Dockerfile Reproducibility

```dockerfile
# Pin base image by digest, not tag
FROM python:3.12-slim@sha256:abc123def456...

# Build-time metadata
ARG PIP_INDEX_URL=https://pypi.org/simple/
ARG BUILD_DATE
LABEL org.opencontainers.image.created=$BUILD_DATE

# Freeze exact versions
COPY requirements.lock /app/
RUN pip install --no-cache-dir -r /app/requirements.lock

# Non-root user for deterministic uid/gid
RUN groupadd -r appuser -g 1000 && useradd -r -g appuser -u 1000 appuser
USER appuser
```

- Never use `:latest` tags — pin to SHA256 digest or at minimum a semantic version.
- Set `--hash` in requirements (pip hash-checking mode) for supply-chain integrity.
- Run `docker build --no-cache` periodically to detect base-image drift.

## pip freeze vs pip-tools

| Aspect | pip freeze | pip-tools (pip-compile) |
|--------|------------|-------------------------|
| Output | Flat installed list | Resolved from pyproject.toml |
| Reproducible | Partial | Yes (deterministic resolver) |
| Sub-deps | Included implicitly | Explicitly pinned |
| Upgrade | Manual re-freeze | `pip-compile --upgrade-pkg foo` |
| CI | Falls out of sync | Lock file checked into repo |

- Use pip-tools or **uv** for production. pip freeze is for debugging only.
- Check in both `requirements.in` and `requirements.txt` (fully pinned lock).
- Validate with `pip install --require-hashes -r requirements.txt` in CI.

## Seed Management Across Frameworks

| Framework | Seed API | Determinism Notes |
|-----------|----------|-------------------|
| Python | `random.seed(42)` | Thread-safe, global |
| NumPy | `np.random.seed(42)` | Legacy; use Generator |
| NumPy v2+ | `rng = np.random.default_rng(42)` | Recommended, per-instance |
| PyTorch | `torch.manual_seed(42)` + `cudnn.deterministic = True` | CuDNN conv needs extra flag |
| TensorFlow | `tf.random.set_seed(42)` | Global and op-level seeds |
| JAX | `key = jax.random.PRNGKey(42)` | Explicit key splitting required |

- Set all seeds at a single entry point (e.g., `experiment.py` line 1).
- Log the full seed set in experiment metadata for audit.
- Distributed training: derive per-worker seeds via `seed + rank`.
