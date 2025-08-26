#!/usr/bin/env bash

set -e

cat /proc/1/environ | tr '\0' '\n' > /etc/systemd.environment

echo "Waiting for RabbitMQ..."
until nc -z "$RABBITMQ_HOST" 5672; do
    echo "RabbitMQ is unavailable - sleeping"
    sleep 3
done

echo "RabbitMQ is up!"

echo "Starting API..."
uvicorn main:app --host 0.0.0.0 --port 8000 &

wait