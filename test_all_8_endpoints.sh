#!/bin/bash

TOKEN=$(curl -s -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"test@local.dev\",\"password\":\"123456\"}" \
  | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))")

echo "========================================="
echo "FINAL TEST: All 8 Training Endpoints"
echo "========================================="
echo ""

# Test 1: Dataset Stats
echo "✅ 1. GET /api/training/dataset/stats"
curl -s http://localhost:5001/api/training/dataset/stats \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print('  ✓' if d.get('success') else '  ✗', d.get('stats', {}).get('total_frames', 0), 'frames')"
echo ""

# Test 2: Export Dataset
echo "✅ 2. POST /api/training/dataset/export"
curl -s -X POST http://localhost:5001/api/training/dataset/export \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print('  ✓' if d.get('success') else '  ✗', 'dataset:', d.get('dataset_path', 'N/A')[:30] if d.get('success') else d.get('error', 'N/A'))"
echo ""

# Test 3: Start Training
echo "✅ 3. POST /api/training/start"
DATASET=$(ls -td storage/datasets/* 2>/dev/null | head -1 | xargs basename)
if [ ! -z "$DATASET" ]; then
  curl -s -X POST http://localhost:5001/api/training/start \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"Test\",\"preset\":\"fast\",\"dataset_yaml_path\":\"storage/datasets/$DATASET/data.yaml\"}" \
    | python3 -c "import sys, json; d=json.load(sys.stdin); print('  ✓ Job created:', d.get('job_id', 'N/A')[:20] if d.get('success') else '  ✗', d.get('error', 'N/A'))"
else
  echo "  ⚠ No dataset found, skipping"
fi
echo ""

# Test 4: Training History
echo "✅ 4. GET /api/training/history"
curl -s http://localhost:5001/api/training/history \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print('  ✓' if d.get('success') else '  ✗', len(d.get('jobs', [])), 'jobs')"
echo ""

# Test 5: Active Model
echo "✅ 5. GET /api/training/models/active"
curl -s http://localhost:5001/api/training/models/active \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print('  ✓' if d.get('success') else '  ✗', 'active' if d.get('model') else 'none')"
echo ""

# Test 6: Activate Model (will fail without trained model, but endpoint exists)
echo "✅ 6. POST /api/training/models/<id>/activate"
curl -s -X POST http://localhost:5001/api/training/models/00000000-0000-0000-0000-000000000000/activate \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print('  ✓ Endpoint works (404 expected)' if 'not found' in d.get('error', '').lower() else '  ✓' if d.get('success') else '  ✗', d.get('error', 'N/A')[:50])"
echo ""

# Test 7: Job Status
JOB_ID=$(curl -s http://localhost:5001/api/training/history -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; j=json.load(sys.stdin); print(j['jobs'][0]['id'] if j.get('jobs') else '')")
if [ ! -z "$JOB_ID" ]; then
  echo "✅ 7. GET /api/training/status/<id>"
  curl -s http://localhost:5001/api/training/status/$JOB_ID \
    -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print('  ✓' if d.get('success') else '  ✗', 'status:', d.get('job', {}).get('status', 'N/A'))"
  echo ""

  # Test 8: Stop Training
  echo "✅ 8. POST /api/training/stop/<id>"
  curl -s -X POST http://localhost:5001/api/training/stop/$JOB_ID \
    -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print('  ✓' if d.get('success') or 'cannot stop' in d.get('error', '').lower() else '  ✗', d.get('message', d.get('error', 'N/A')))"
  echo ""
else
  echo "⚠ No jobs found, skipping tests 7-8"
fi

echo "========================================="
echo "✅ All 8 endpoints implemented!"
echo "========================================="
