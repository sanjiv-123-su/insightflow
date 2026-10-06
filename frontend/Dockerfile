# ==============================================================================
# InsightFlow Frontend Dockerfile (Multi-stage: Node.js 20 build -> Nginx Alpine)
# ==============================================================================

# Stage 1: Build the React + Vite static bundle
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies with frozen lockfile
COPY package.json package-lock.json ./
RUN npm ci

# Copy frontend source
COPY . .

# Build-time argument for backend URL (empty string enables Nginx reverse proxying)
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

# Build production assets into /app/dist
RUN npm run build

# Stage 2: Serve static files with production Nginx
FROM nginx:alpine

# Remove default nginx static page
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx configuration with SPA routing and API proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Healthcheck testing HTTP response on root path
HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
