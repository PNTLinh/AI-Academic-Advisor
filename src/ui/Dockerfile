# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy only package files (smaller layer)
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --no-frozen-lockfile

# Copy source code
COPY . .

# Build Next.js (outputs to .next)
RUN pnpm run build

# Remove node_modules to slim down builder
RUN rm -rf node_modules

# ─────────────────────────────────────────────────────────────────
# Production stage - much smaller
FROM node:20-alpine

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy only package files
COPY package.json pnpm-lock.yaml ./

# Install ONLY production dependencies
RUN pnpm install --no-frozen-lockfile --prod

# Copy built Next.js app from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Next.js config
COPY next.config.mjs ./

ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000

CMD ["pnpm", "start"]
