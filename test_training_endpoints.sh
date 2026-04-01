#!/bin/bash

# Get token first
TOKEN=$(curl -s -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"test@local.dev\",\"password\":\"123456\"}" \
  | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))")

echo "========================================="
echo "Testing Training Control Endpoints"
echo "========================================="
echo ""
echo "Token: ${TOKEN:0:30}..."
echo ""

# Test 1: Dataset Stats
echo "Test 1: GET /api/training/dataset/stats"
echo "----------------------------------------"
curl -s http://localhost:5001/api/training/dataset/stats \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""
echo ""

# Test 2: Export Dataset (will fail if no frames, but endpoint should work)
echo "Test 2: POST /api/training/dataset/export"
echo "------------------------------------------"
RESPONSE=$(curl -s -X POST http://localhost:5001/api/training/dataset/export \
  -H "Authorization: Bearer $TOKEN")
echo "$RESPONSE" | python3 -m json.tool || echo "$RESPONSE"
echo ""
echo ""

# Test 3: Start Training (will fail without dataset, but endpoint should work)
echo "Test 3: POST /api/training/start"
echo "---------------------------------"
RESPONSE=$(curl -s -X POST http://localhost:5001/api/training/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Job","preset":"fast","dataset_yaml_path":"/tmp/fake.yaml"}')
echo "$RESPONSE" | python3 -m json.tool || echo "$RESPONSE"
echo ""
echo ""

# Test 4: Training History (should be empty)
echo "Test 4: GET /api/training/history"
echo "----------------------------------"
curl -s http://localhost:5001/api/training/history \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""
echo ""

# Test 5: Active Model (should be null/none)
echo "Test 5: GET /api/training/models/active"
echo "----------------------------------------"
curl -s http://localhost:5001/api/training/models/active \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""
echo ""

echo "========================================="
echo "All endpoints tested!"
echo "========================================="
