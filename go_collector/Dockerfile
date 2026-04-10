FROM golang:1.22-alpine AS builder
WORKDIR /app

# Cache dependencies (no go.sum — stdlib only)
COPY go.mod ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o go_collector .

FROM scratch
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /app/go_collector /go_collector
EXPOSE 8082
ENTRYPOINT ["/go_collector"]
