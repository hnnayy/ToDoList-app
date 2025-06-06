#!/bin/bash

set -e

echo "🚀 Starting deployment process..."

# Variables
APP_NAME="todolist-app"
ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}

echo "📋 Deploying $APP_NAME to $ENVIRONMENT environment (version: $VERSION)"

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t $APP_NAME:$VERSION .

# Tag for registry (if using one)
docker tag $APP_NAME:$VERSION $APP_NAME:$ENVIRONMENT-latest

# Run pre-deployment tests
echo "🧪 Running pre-deployment tests..."
docker run --rm $APP_NAME:$VERSION python -m pytest tests/ -v

# Deploy using docker-compose
echo "🚢 Deploying application..."
if [ "$ENVIRONMENT" = "staging" ]; then
    docker-compose -f docker-compose.staging.yml up -d
else
    docker-compose up -d
fi

# Wait for application to be ready
echo "⏳ Waiting for application to be ready..."
sleep 10

# Health check
echo "🏥 Performing health check..."
if curl -f http://localhost:5000/health; then
    echo "✅ Deployment successful!"
else
    echo "❌ Deployment failed - health check failed"
    exit 1
fi

echo "🎉 Deployment completed successfully!"
