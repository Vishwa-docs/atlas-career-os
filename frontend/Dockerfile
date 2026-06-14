# Atlas frontend. Dev: docker compose runs `npm install && npm run dev`.
# Production: multi-stage build to static assets served by nginx (used by Vercel
# directly via its own build; this image is for self-hosting / parity).
FROM node:22-slim AS dev
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

FROM node:22-slim AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
