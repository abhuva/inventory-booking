FROM node:23-slim AS build

WORKDIR /app

ARG PUBLIC_API_BASE_URL=http://127.0.0.1:8000
ARG PUBLIC_APP_BASE_URL=http://127.0.0.1:5173
ENV PUBLIC_API_BASE_URL=$PUBLIC_API_BASE_URL \
    PUBLIC_APP_BASE_URL=$PUBLIC_APP_BASE_URL

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:23-slim AS runtime

ENV NODE_ENV=production
WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY --from=build /app/build ./build

EXPOSE 3000
CMD ["node", "build"]
