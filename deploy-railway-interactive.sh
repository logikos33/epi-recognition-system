#!/bin/bash

# Railway Interactive Deploy Script
# Execute este script APÓS fazer login com 'railway login'

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         🚀 Railway Deploy - EPI Recognition System          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if logged in
echo "🔐 Checking authentication..."
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged in to Railway!"
    echo "Please run: railway login"
    exit 1
fi

USER=$(railway whoami)
echo "✅ Logged in as: $USER"
echo ""

# Initialize project
echo "📦 Initializing Railway project..."
if [ -f "railway-up.json" ]; then
    echo "⚠️  Project already initialized (railway-up.json exists)"
    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
else
    railway init --name "epi-recognition-api"
fi
echo ""

# Set variables
echo "⚙️  Setting environment variables..."

# Generate JWT secret
JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || echo "change-this-secret-key-in-production")

echo "Setting JWT_SECRET_KEY..."
railway variables set JWT_SECRET_KEY="$JWT_SECRET"

echo "Setting PORT..."
railway variables set PORT=5001

echo "Setting PYTHONUNBUFFERED..."
railway variables set PYTHONUNBUFFERED=1

echo ""
echo "✅ Variables set!"
echo ""

# Add PostgreSQL
echo "🗄️  Setting up PostgreSQL database..."
echo ""
echo "About to add PostgreSQL service..."
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    railway add postgresql

    echo ""
    echo "⏳ Waiting for database to be ready..."
    sleep 5

    echo ""
    echo "✅ PostgreSQL added!"
    echo ""
    echo "📝 DATABASE_URL will be automatically set by Railway"
fi
echo ""

# Deploy
echo "🚀 Deploying to Railway..."
echo ""
read -p "Ready to deploy? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "⏳ Uploading code and starting deployment..."
    railway up --detach

    echo ""
    echo "✅ Deployment started!"
    echo ""
    echo "⏳ Waiting for deployment to complete..."
    echo "This may take 5-10 minutes on first deploy..."
    echo ""

    # Wait and check status
    for i in {1..12}; do
        sleep 10
        echo "⏳ Checking status... ($i/12)"

        STATUS=$(railway status --json 2>/dev/null | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)

        if [ "$STATUS" = "READY" ] || [ "$STATUS" = "SUCCESS" ]; then
            echo "✅ Deployment successful!"
            break
        elif [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "ERROR" ]; then
            echo "❌ Deployment failed!"
            echo "Check logs with: railway logs"
            exit 1
        fi
    done

    echo ""
    echo "🎉 Deployment complete!"
    echo ""
fi

# Get domain
echo "🌐 Getting deployment URL..."
DOMAIN=$(railway domain --quiet 2>/dev/null || echo "")
if [ ! -z "$DOMAIN" ]; then
    echo "✅ API URL: https://$DOMAIN"
    echo ""
    echo "Add this to your frontend .env.local:"
    echo "NEXT_PUBLIC_API_URL=https://$DOMAIN"
    echo ""
fi

# Database setup instructions
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                   📋 POST-DEPLOY STEPS                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "1. ⏳ Wait 2-3 minutes for service to fully start"
echo ""
echo "2. 🗄️  Set up database schema:"
echo "   railway variables | grep DATABASE_URL"
echo "   psql <URL> < railway-database-schema.sql"
echo ""
echo "3. 🔍 Check deployment status:"
echo "   railway status"
echo ""
echo "4. 📊 View logs:"
echo "   railway logs"
echo ""
echo "5. 🧪 Test health endpoint:"
if [ ! -z "$DOMAIN" ]; then
    echo "   curl https://$DOMAIN/health"
else
    echo "   curl https://<your-domain>/health"
fi
echo ""
echo "6. 🌐 Open in browser:"
echo "   railway open"
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  ✅ ALL SET!                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
