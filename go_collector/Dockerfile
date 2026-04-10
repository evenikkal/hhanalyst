FROM golang:1.21-alpine AS builder
WORKDIR /app

# Cache dependencies
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o go_collector .

FROM scratch
COPY --from=builder /app/go_collector /go_collector
EXPOSE 8082
ENTRYPOINT ["/go_collector"]
