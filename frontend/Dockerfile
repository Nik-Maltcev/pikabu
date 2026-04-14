FROM node:20-alpine AS build

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
RUN npm install -g serve
COPY --from=build /app/dist /app/dist
WORKDIR /app
EXPOSE 3000
CMD ["serve", "dist", "-s", "-l", "3000"]
