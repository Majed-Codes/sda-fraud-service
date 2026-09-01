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

COPY requirements.lock ./
# Everything that shrinks the venv happens HERE, before it is copied into the
# runtime stage. Deleting in the runtime stage only adds whiteout entries - the
# bytes stay in the layer that already shipped them.
RUN pip install -r requirements.lock \
 && find /opt/venv -type d -name tests -prune -exec rm -rf {} + \
 && find /opt/venv -type f -name '*.so' -exec strip --strip-unneeded {} + \
 && rm -rf /opt/venv/lib/python*/site-packages/pip \
           /opt/venv/lib/python*/site-packages/pip-*.dist-info \
           /opt/venv/lib/python*/site-packages/setuptools \
           /opt/venv/lib/python*/site-packages/setuptools-*.dist-info \
           /opt/venv/lib/python*/site-packages/pkg_resources \
           /opt/venv/bin/pip /opt/venv/bin/pip3 /opt/venv/bin/pip3.* \
 && find /opt/venv -name '*.pyi' -delete

COPY pyproject.toml ./
COPY src ./src
# The venv's own pip was pruned above, so build the wheel with the base
# image's interpreter - it never ships either way.
RUN /usr/local/bin/python -m pip wheel --no-deps --wheel-dir /wheels .


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

# A wheel is a zip of an already-built pure-Python package, so it unpacks with
# the stdlib. That keeps pip out of the runtime image entirely, and keeps this
# layer small and independent of the venv above it.
COPY --from=builder /wheels /wheels
# Destination derived, never hardcoded: `zipfile -e` creates whatever path it
# is given, so a base-image bump would silently extract into a directory that
# is not on sys.path and the container would start and die on import.
RUN SITE="$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')" \
 && python -m zipfile -e /wheels/*.whl "$SITE" \
 && rm -rf /wheels \
 && rm -rf /usr/local/lib/python*/site-packages/pip \
           /usr/local/lib/python*/site-packages/pip-*.dist-info \
           /usr/local/lib/python*/site-packages/setuptools \
           /usr/local/lib/python*/site-packages/setuptools-*.dist-info \
           /usr/local/lib/python*/site-packages/pkg_resources \
           /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.*

WORKDIR /app
COPY --chown=app:app models ./models

USER app

EXPOSE 8000

HEALTHCHECK --interval=5s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/v1/ready', timeout=2).status == 200 else 1)"]

CMD ["uvicorn", "--factory", "fraud_service.api.app:create_app", "--host", "0.0.0.0", "--port", "8000"]
