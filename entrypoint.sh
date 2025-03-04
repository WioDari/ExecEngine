#!/usr/bin/env bash

set -e

echo "Waiting for RabbitMQ..."
until nc -z "$RABBITMQ_HOST" 5672; do
    echo "RabbitMQ is unavailable - sleeping"
    sleep 3
done

echo "RabbitMQ is up!"

echo "Starting API..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir .
