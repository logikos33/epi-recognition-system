#!/bin/bash

# Script para conectar ao projeto Railway existente

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🔗 Connect to Existing Railway Project                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if logged in
echo "🔐 Checking authentication..."
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged in!"
    echo ""
    echo "Please get your token from: https://railway.app/account/api-tokens"
    echo "Then run: railway login --token <your-token>"
    echo ""
    read -p "Enter your Railway token: " TOKEN
    railway login --token "$TOKEN"
fi

USER=$(railway whoami)
echo "✅ Logged in as: $USER"
echo ""

# List existing projects
echo "📋 Listing your Railway projects..."
echo ""
railway projects
echo ""

# Ask which project to connect
echo "Enter the Project ID or name you want to connect to:"
read -p "> " PROJECT_ID

if [ ! -z "$PROJECT_ID" ]; then
    echo ""
    echo "🔗 Connecting to project: $PROJECT_ID"
    railway link "$PROJECT_ID"
    
    echo ""
    echo "✅ Connected!"
    echo ""
    
    # Show current services
    echo "📊 Current services in project:"
    railway status
    echo ""
    
    # Show variables
    echo "⚙️  Current environment variables:"
    railway variables
    echo ""
    
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ✅ CONNECTED TO RAILWAY PROJECT              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Next steps:"
    echo "1. railway status          - Check services"
    echo "2. railway up              - Deploy/update code"
    echo "3. railway logs            - View logs"
    echo "4. railway open            - Open in browser"
fi
