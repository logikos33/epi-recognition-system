#!/bin/bash

echo "=========================================="
echo "🚀 Quick Deploy to Railway"
echo "=========================================="
echo ""

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged in to Railway!"
    echo ""
    echo "Please login first:"
    echo "  railway login"
    echo ""
    exit 1
fi

echo "✅ Logged in as: $(railway whoami)"
echo ""

# Link to project
echo "🔗 Linking to project..."
railway link 366c8fae-197b-4e55-9ec9-b5261b3f4b62
echo ""

# Show status
echo "📊 Project Status:"
railway status
echo ""

# Show variables
echo "⚙️  Environment Variables:"
railway variables
echo ""

read -p "Ready to deploy? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Deploying..."
    railway up
    echo ""
    echo "✅ Deploy started!"
    echo ""
    echo "Monitor: railway logs"
fi
