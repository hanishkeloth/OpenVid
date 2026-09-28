FROM node:22-bookworm-slim AS node-runtime
FROM python:3.13-slim-bookworm
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libreoffice-impress fonts-liberation fonts-dejavu-core fonts-noto-cjk fonts-noto-color-emoji \
    curl ca-certificates unzip libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV HYPERFRAMES_NO_UPDATE_CHECK=1 DO_NOT_TRACK=1 PYTHONUNBUFFERED=1
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && ./node_modules/.bin/hyperframes browser ensure
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY web ./web
COPY scripts ./scripts
COPY examples ./examples
COPY LICENSE NOTICE.md README.md ./
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh
ENV OPENVID_DATA_DIR=/data OPENVID_RENDER_WORKERS=2 PORT=7795
EXPOSE 7795
VOLUME ["/data"]
ENTRYPOINT ["./docker-entrypoint.sh"]
