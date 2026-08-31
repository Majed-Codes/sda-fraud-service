FROM python:3.13-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv

WORKDIR /build

COPY requirements.txt ./
RUN pip install -r requirements.txt \
 && find /opt/venv -type d -name tests -prune -exec rm -rf {} + \
 && find /opt/venv -type f -name '*.so' -exec strip --strip-unneeded {} +

COPY pyproject.toml ./
COPY src ./src
RUN pip wheel --no-deps --wheel-dir /wheels .


FROM python:3.13-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home app

COPY --from=builder /opt/venv /opt/venv

COPY --from=builder /wheels /wheels
RUN pip install --no-deps /wheels/*.whl \
 && rm -rf /wheels /opt/venv/lib/python3.13/site-packages/pip \
           /opt/venv/lib/python3.13/site-packages/pip-*.dist-info \
           /opt/venv/lib/python3.13/site-packages/setuptools \
           /opt/venv/lib/python3.13/site-packages/setuptools-*.dist-info \
           /opt/venv/lib/python3.13/site-packages/pkg_resources

WORKDIR /app
COPY --chown=app:app models ./models

USER app

EXPOSE 8000

HEALTHCHECK --interval=5s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/v1/ready', timeout=2).status == 200 else 1)"]

CMD ["uvicorn", "fraud_service.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
