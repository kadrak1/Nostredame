# --- Stage 1: Build ---
FROM node:20-slim AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# --- Stage 2: Copy dist to shared volume ---
# Caddy serves the built files in production.
# This container copies the build output and exits.
FROM alpine:3.19

COPY --from=build /app/dist /dist
CMD ["cp", "-r", "/dist/.", "/output/"]
