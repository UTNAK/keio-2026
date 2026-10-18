FROM quay.io/jupyter/minimal-notebook:2026-07-28 AS jupyter-base

ARG OPENSYSML_KERNEL_VERSION=0.9.3.dev20261008
ARG OPENCODE_VERSION=1.19.0

ENV DEBIAN_FRONTEND=noninteractive \
    JUPYTER_ENABLE_LAB=yes \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER root

RUN apt-get update \
    && apt-get install --no-install-recommends --yes ca-certificates curl graphviz \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir \
        --requirement /tmp/requirements.txt \
        "jupyter-opensysml-kernel==${OPENSYSML_KERNEL_VERSION}" \
    && python -m jupyter kernelspec list \
    && test -d "$(python -c 'import sysconfig; print(sysconfig.get_path("data"))')/share/jupyter/kernels/sysml"

COPY course_evidence /opt/course/course_evidence
COPY opencode /opt/course/opencode
COPY .opencode /opt/course/.opencode
RUN touch /opt/course/.opencode/.gitignore
COPY docs/classroom-data-and-privacy.md /opt/course/docs/classroom-data-and-privacy.md
COPY docs/first_model.md /opt/course/docs/first_model.md
COPY config/jupyter/keio_course_evidence.json /opt/conda/etc/jupyter/jupyter_server_config.d/keio_course_evidence.json
ENV PYTHONPATH=/opt/course

WORKDIR /home/jovyan/work

# Compose starts this image as root so the Jupyter Docker Stacks startup
# script can rename jovyan to NB_USER and then drop privileges.
USER root
ARG TARGETARCH
# OpenCode 1.19.0 ACP persona supports OpenCode >=1.0,<2. These release
# archives and SHA-256 digests are published for Linux amd64 and arm64.
RUN case "$TARGETARCH" in \
      amd64) artifact=x64-baseline; digest=6334d70db3990721ea454357e9cf2573c8685524ad7769af9d52cbffb7008438 ;; \
      arm64) artifact=arm64; digest=e9841d43d3e1a8f36ed2691592d3b8b4fb097e606c8b559a277a1b845840e26b ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac \
    && curl --fail --location --retry 3 "https://github.com/anomalyco/opencode/releases/download/v${OPENCODE_VERSION}/opencode-linux-${artifact}.tar.gz" -o /tmp/opencode.tar.gz \
    && echo "$digest  /tmp/opencode.tar.gz" | sha256sum --check - \
    && tar -xzf /tmp/opencode.tar.gz -C /usr/local/bin \
    && rm /tmp/opencode.tar.gz \
    && chmod 0755 /usr/local/bin/opencode

ENV HOME=/home/keio \
    XDG_DATA_HOME=/home/keio/state/data \
    XDG_CONFIG_HOME=/home/keio/state/config \
    XDG_CACHE_HOME=/home/keio/state/cache \
    XDG_STATE_HOME=/home/keio/state/state \
    COURSE_DATA_DIR=/home/keio/work/private-course-data \
    COURSE_QUESTION_BANK_PATH=/opt/course/opencode/question-bank.json \
    COURSE_SYNC_INTERVAL=120 \
    OPENCODE_CONFIG=/opt/course/opencode/opencode.json \
    OPENCODE_CONFIG_DIR=/opt/course/.opencode \
    OPENCODE_DISABLE_AUTOUPDATE=true

FROM node:22.23.1-bookworm-slim AS classroom-status-extension
WORKDIR /build
COPY labextension/package*.json ./
RUN npm ci
COPY labextension/src ./src
COPY labextension/style ./style
COPY --from=jupyter-base /opt/conda/lib/python3.13/site-packages/jupyterlab/staging /core
RUN npm run build -- --core-path /core

FROM jupyter-base
COPY --from=classroom-status-extension /build/keio_classroom_status/labextension /opt/conda/share/jupyter/labextensions/@keio/classroom-status
