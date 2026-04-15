FROM node:22-slim

ENV DEBIAN_FRONTEND=noninteractive \
    NODE_ENV=production \
    HOME=/home/node \
    OPENCLAW_CONFIG_DIR=/home/node/.openclaw \
    PATH=/usr/local/bin:/usr/bin:/bin

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-yaml ca-certificates jq tini git \
    && rm -rf /var/lib/apt/lists/*

# Overridable at build time:
#   docker build --build-arg OPENCLAW_PKG=openclaw@<ver> --build-arg ACPX_PKG=acpx@<ver> .
ARG OPENCLAW_PKG="openclaw@2026.4.14"
ARG ACPX_PKG="acpx@0.5.3"

RUN npm install -g --omit=dev "${OPENCLAW_PKG}" "${ACPX_PKG}" \
    && npm cache clean --force

COPY --chown=root:root config/       /opt/trajrec/config/
COPY --chown=root:root skills/       /opt/trajrec/skills/
COPY --chown=root:root entrypoint.sh /opt/trajrec/entrypoint.sh
RUN chmod 0755 /opt/trajrec/entrypoint.sh \
               /opt/trajrec/skills/web_search/run.py \
               /opt/trajrec/skills/web_search/mcp_server.py

USER node
WORKDIR /home/node

ENTRYPOINT ["/usr/bin/tini", "--", "/opt/trajrec/entrypoint.sh"]
