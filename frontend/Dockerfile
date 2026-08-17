FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com \
    && npm ci --fetch-retries=5 --fetch-retry-mintimeout=2000 --fetch-retry-maxtimeout=120000
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]
