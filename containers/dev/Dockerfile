# syntax=docker/dockerfile:1

FROM python:3.14.7-slim-bookworm

ARG UV_VERSION=0.12.19

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --disable-pip-version-check --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /workspace

CMD ["bash"]
