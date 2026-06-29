FROM node:26-alpine AS builder
WORKDIR /app

# Lockfile + manifest first for caching
COPY package*.json ./
RUN npm ci --no-audit --no-fund

# Source
COPY . .

# Next.js production build
RUN npm run build

FROM node:26-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Drop privileges
RUN addgroup -S app && adduser -S app -G app

COPY --from=builder --chown=app:app /app/.next ./.next
COPY --from=builder --chown=app:app /app/node_modules ./node_modules
COPY --from=builder --chown=app:app /app/package.json ./package.json
COPY --from=builder --chown=app:app /app/public ./public

USER app
EXPOSE 3000
CMD ["npm", "start"]
