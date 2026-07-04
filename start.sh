#!/bin/bash
echo "Starting FeatureFlow in Production Mode..."
if [ ! -f .env ]; then
    echo "Creating .env from .env.example"
    cp .env.example .env
fi
docker-compose up --build -d
echo "FeatureFlow is running!"
echo "- Dashboard: http://localhost:3000"
echo "- API: http://localhost:8000/api/v1/platform"
