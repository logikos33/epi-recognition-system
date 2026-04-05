#!/bin/bash

# Script específico para conectar ao projeto Railway

PROJECT_ID="366c8fae-197b-4e55-9ec9-b5261b3f4b62"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🔗 Connect to Railway Project                          ║"
echo "║     Project ID: $PROJECT_ID                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo "🔐 Please login to Railway first"
    echo ""
    echo "Option 1: Browser login"
    echo "  Run: railway login"
    echo ""
    echo "Option 2: Token login"
    echo "  1. Get token from: https://railway.app/account/api-tokens"
    echo "  2. Run: railway login --token <your-token>"
    echo ""
    exit 1
fi

USER=$(railway whoami)
echo "✅ Logged in as: $USER"
echo ""

# Connect to project
echo "🔗 Connecting to project..."
railway link "$PROJECT_ID"

echo ""
echo "✅ Connected to project!"
echo ""

# Show current status
echo "📊 Project Status:"
echo ""
railway status
echo ""

# Show services
echo "🔧 Services:"
echo ""
railway services
echo ""

# Show variables
echo "⚙️  Environment Variables:"
echo ""
railway variables
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✅ READY TO DEPLOY                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Next commands:"
echo "  railway up              - Deploy/update code"
echo "  railway logs            - View logs"
echo "  railway open            - Open project in browser"
