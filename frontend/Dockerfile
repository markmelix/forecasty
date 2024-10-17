FROM alpine:3.20

WORKDIR /app

RUN apk upgrade --no-cache && apk add --no-cache libgcc gcc musl-dev bind-tools yaml-dev yarn

COPY . .

RUN yarn --frozen-lockfile --link-duplicates --network-timeout 500000

CMD ["yarn", "dev"]
