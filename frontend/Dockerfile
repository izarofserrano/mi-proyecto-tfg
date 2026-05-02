# ── Stage 1: build ───────────────────────────────────────────────────────
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --silent

COPY . .

# In production the nginx proxy handles /api → backend,
# so VITE_API_URL is left empty (requests use relative paths).
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Stage 2: serve ───────────────────────────────────────────────────────
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Remove the default nginx config
RUN rm -f /etc/nginx/conf.d/default.conf.dpkg-old

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
