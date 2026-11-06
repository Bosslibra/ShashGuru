FROM node:20-alpine as build-stage

WORKDIR /app

# Build-time frontend configuration (public values only: they end up in the JavaScript bundle).
ARG VITE_AUTH_PROVIDER=none
ARG VITE_CLERK_PUBLISHABLE_KEY=
ENV VITE_AUTH_PROVIDER=$VITE_AUTH_PROVIDER \
    VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY

COPY frontend/package*.json ./
RUN npm ci || npm install

COPY frontend/ .
RUN npm run build

FROM nginx:stable-alpine as production-stage

COPY --from=build-stage /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
