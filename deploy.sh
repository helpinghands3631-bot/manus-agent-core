#!/bin/bash

# Manus Agent Core - Quick Deploy Script
# Deploys the agent using Docker Compose

set -e

echo "🚀 Manus Agent Core Deployment"
echo "================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit it with your API keys."
    echo ""
    echo "Required: Add your GROQ_API_KEY to .env"
    echo "Optional: Configure other LLM providers (OpenAI, Anthropic, Ollama)"
    echo ""
    read -p "Press Enter after editing .env file..."
fi

# Validate GROQ_API_KEY exists
if ! grep -q "GROQ_API_KEY=gsk_" .env; then
    echo "❌ GROQ_API_KEY not set in .env file"
    echo "Please add your Grok API key to .env"
    exit 1
fi

echo "✅ Configuration validated"
echo ""

# Build and start containers
echo "🔨 Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting Manus Agent..."
docker-compose up -d

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 View logs: docker-compose logs -f"
echo "🛑 Stop agent: docker-compose down"
echo "🔄 Restart: docker-compose restart"
echo ""
echo "Agent is now running and ready to execute tasks!"
