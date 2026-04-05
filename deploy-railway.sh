#!/bin/bash

# Railway Deploy Script for EPI Recognition System
# This script helps deploy the backend API to Railway

set -e

echo "=================================="
echo "🚀 Railway Deploy Script"
echo "=================================="
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "⚠️  Railway CLI not found!"
    echo "Installing Railway CLI..."
    npm install -g @railway/cli
    echo ""
fi

# Check if user is logged in
echo "🔐 Checking Railway authentication..."
if ! railway whoami &> /dev/null; then
    echo "Please login to Railway:"
    railway login
    echo ""
fi

echo "✅ Authenticated successfully!"
echo ""

# Initialize Railway project
echo "📦 Initializing Railway project..."
if [ ! -f "railway-up.json" ]; then
    echo "Creating new Railway project..."
    railway init
    echo ""
else
    echo "Railway project already initialized"
    echo ""
fi

# Add PostgreSQL database
echo "🗄️  Setting up PostgreSQL database..."
echo "Run: railway add postgresql"
echo "After adding, copy the DATABASE_URL from: railway variables"
echo ""

# Set environment variables
echo "⚙️  Setting environment variables..."
echo "Required variables:"
echo "  - JWT_SECRET_KEY (generate a strong secret key)"
echo "  - DATABASE_URL (automatically set by Railway PostgreSQL)"
echo ""

# Generate JWT secret
JWT_SECRET=$(openssl rand -hex 32)
echo "Generated JWT_SECRET_KEY: $JWT_SECRET"
echo ""

# Ask user to continue
read -p "Do you want to deploy now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Deploying to Railway..."
    railway up
    echo ""
    echo "✅ Deployment started!"
    echo ""
    echo "Check deployment status: railway status"
    echo "View logs: railway logs"
    echo "Open app: railway domain"
else
    echo "Deployment cancelled"
fi

echo ""
echo "=================================="
echo "📝 Post-Deploy Steps"
echo "=================================="
echo ""
echo "1. Add PostgreSQL database:"
echo "   railway add postgresql"
echo ""
echo "2. Execute database schema:"
echo "   railway variables (get DATABASE_URL)"
echo "   psql $DATABASE_URL < railway-database-schema.sql"
echo ""
echo "3. Set JWT_SECRET_KEY:"
echo "   railway variables set JWT_SECRET_KEY=$JWT_SECRET"
echo ""
echo "4. Check deployment:"
echo "   railway status"
echo "   railway logs"
echo ""
echo "5. Get your API URL:"
echo "   railway domain"
echo ""
echo "=================================="
