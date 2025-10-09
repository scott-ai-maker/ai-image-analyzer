#!/bin/bash

# Test script for AI Image Analyzer Backend

set -euo pipefail

echo "🧪 Testing AI Image Analyzer Backend"
echo "=================================="

# Configuration
BACKEND_URL="${1:-http://localhost:8000}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Helper functions
test_endpoint() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    local description="$3"

    echo -n "Testing $description... "

    response=$(curl -s -w "%{http_code}" -o /tmp/response.json "$BACKEND_URL$endpoint" || echo "000")

    if [[ "$response" == "$expected_status" ]]; then
        echo -e "${GREEN}✅ PASS${NC}"
        return 0
    else
        echo -e "${RED}❌ FAIL (HTTP $response)${NC}"
        if [[ -f /tmp/response.json ]]; then
            echo "Response: $(cat /tmp/response.json)"
        fi
        return 1
    fi
}

# Test health endpoint
echo ""
echo "🏥 Health Check Tests"
echo "-------------------"
test_endpoint "/health" "200" "Health endpoint"

if [[ -f /tmp/response.json ]]; then
    echo "Health Response:"
    cat /tmp/response.json | python3 -m json.tool 2>/dev/null || cat /tmp/response.json
    echo ""
fi

# Test API endpoints
echo ""
echo "🔧 API Endpoint Tests"
echo "-------------------"
test_endpoint "/api/test" "200" "Test endpoint"
test_endpoint "/api/status" "200" "Status endpoint"
test_endpoint "/api/demo-info" "200" "Demo info endpoint"

# Test rate limiting
echo ""
echo "⏱️ Rate Limiting Tests"
echo "--------------------"
echo "Testing rate limiting (sending 12 requests rapidly)..."

success_count=0
rate_limit_count=0

for i in {1..12}; do
    response=$(curl -s -w "%{http_code}" -o /dev/null "$BACKEND_URL/api/test" 2>/dev/null || echo "000")
    if [[ "$response" == "200" ]]; then
        ((success_count++))
    elif [[ "$response" == "429" ]]; then
        ((rate_limit_count++))
    fi
    echo -n "."
done

echo ""
echo "Results: $success_count successful, $rate_limit_count rate limited"

if [[ $rate_limit_count -gt 0 ]]; then
    echo -e "${GREEN}✅ Rate limiting is working!${NC}"
else
    echo -e "${YELLOW}⚠️  Rate limiting may not be working (all requests succeeded)${NC}"
fi

# Test invalid image upload
echo ""
echo "📸 Image Upload Tests"
echo "-------------------"
echo "Testing invalid file upload..."

# Create a test text file
echo "This is not an image" > /tmp/test.txt

response=$(curl -s -w "%{http_code}" -o /tmp/upload_response.json \
    -X POST \
    -F "file=@/tmp/test.txt" \
    "$BACKEND_URL/api/analyze-image" 2>/dev/null || echo "000")

if [[ "$response" == "400" ]]; then
    echo -e "${GREEN}✅ Invalid file rejection working${NC}"
else
    echo -e "${RED}❌ Invalid file rejection failed (HTTP $response)${NC}"
    if [[ -f /tmp/upload_response.json ]]; then
        cat /tmp/upload_response.json
    fi
fi

# Clean up
rm -f /tmp/response.json /tmp/upload_response.json /tmp/test.txt

echo ""
echo "🎯 Test Summary"
echo "=============="
echo "Backend URL: $BACKEND_URL"
echo "All basic functionality tests completed!"
echo ""
echo "To test with real images:"
echo "  curl -X POST -F 'file=@your-image.jpg' $BACKEND_URL/api/analyze-image"
echo ""
echo "To view API documentation:"
echo "  Open: $BACKEND_URL/docs"
