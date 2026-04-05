#!/bin/bash
# E2E Test Runner for HLS Streaming System

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     HLS Streaming E2E Test Runner                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Change to script directory
cd "$(dirname "$0")"

# Check if API server is running
echo -e "${YELLOW}[CHECK]${NC} Checking if API server is running..."
if curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅${NC} API server is running"
else
    echo -e "${RED}❌${NC} API server is not running!"
    echo ""
    echo "Please start the API server first:"
    echo "  cd \"$(pwd)\""
    echo "  source venv/bin/activate"
    echo "  export $(cat .env 2>/dev/null | grep -v '^#' | xargs)"
    echo "  python api_server.py"
    echo ""
    exit 1
fi

# Check FFmpeg
echo -e "${YELLOW}[CHECK]${NC} Checking FFmpeg installation..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n 1)
    echo -e "${GREEN}✅${NC} FFmpeg is installed: $FFMPEG_VERSION"
else
    echo -e "${YELLOW}⚠️${NC} FFmpeg not installed - stream tests will be skipped"
    echo "  Install: brew install ffmpeg (macOS)"
fi

# Check PostgreSQL
echo -e "${YELLOW}[CHECK]${NC} Checking database connection..."
if python3 -c "from backend.database import get_db; next(get_db())" 2>/dev/null; then
    echo -e "${GREEN}✅${NC} Database connection successful"
else
    echo -e "${RED}❌${NC} Database connection failed!"
    echo "  Check DATABASE_URL in .env file"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Running E2E Tests..."
echo "═══════════════════════════════════════════════════════════"
echo ""

# Run tests
python3 -m pytest tests/test_e2e_hls_streaming.py -v -s "$@"

# Capture exit code
TEST_EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All E2E tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed${NC}"
fi
echo "═══════════════════════════════════════════════════════════"

exit $TEST_EXIT_CODE
