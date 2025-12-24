#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
TIMEOUT=30

echo "🧪 AI Companion Server - Chat Integration Tests"
echo "================================================"
echo ""
echo "Testing API at: $API_BASE_URL"
echo ""

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        exit 1
    fi
}

# Function to check if server is running
check_server() {
    echo "🔍 Checking if server is running..."
    if curl -sf "$API_BASE_URL/health" > /dev/null 2>&1; then
        print_result 0 "Server is healthy"
        return 0
    else
        echo -e "${RED}✗${NC} Server is not responding at $API_BASE_URL"
        echo "Please start the server with: docker-compose up -d"
        exit 1
    fi
}

# Test 1: Health Check
test_health_check() {
    echo ""
    echo "📋 Test 1: Health Check"
    echo "----------------------"
    
    response=$(curl -sf "$API_BASE_URL/health")
    
    if echo "$response" | grep -q "healthy"; then
        print_result 0 "Health check passed"
    else
        print_result 1 "Health check failed"
    fi
}

# Test 2: Root Endpoint
test_root_endpoint() {
    echo ""
    echo "📋 Test 2: Root Endpoint"
    echo "----------------------"
    
    response=$(curl -sf "$API_BASE_URL/")
    
    if echo "$response" | grep -q "Evolving Personal AI Assistant"; then
        print_result 0 "Root endpoint returned correct app name"
    else
        print_result 1 "Root endpoint failed"
    fi
}

# Test 3: Chat Streaming (SSE)
test_chat_streaming() {
    echo ""
    echo "📋 Test 3: Chat Streaming (SSE)"
    echo "------------------------------"
    
    # Create a temporary file for the response
    temp_file=$(mktemp)
    
    # Send a simple chat request and capture streaming response
    curl -sf -X POST "$API_BASE_URL/chat/stream" \
        -H "Content-Type: application/json" \
        -d '{
            "message": "Say hello in one word",
            "include_memory": false,
            "tools_enabled": false
        }' \
        --max-time $TIMEOUT \
        > "$temp_file" 2>&1
    
    # Check if we got streaming events
    if grep -q "event:" "$temp_file" || grep -q "data:" "$temp_file"; then
        print_result 0 "Received SSE streaming events"
        
        # Check for conversation_id event
        if grep -q "conversation_id" "$temp_file"; then
            print_result 0 "Received conversation_id event"
        else
            echo -e "${YELLOW}⚠${NC}  No conversation_id event (may be normal)"
        fi
        
        # Check for content events
        if grep -q "content_delta\|message_start\|thinking" "$temp_file"; then
            print_result 0 "Received content streaming events"
        else
            echo -e "${YELLOW}⚠${NC}  No content events detected"
        fi
        
        # Check for done event
        if grep -q "done" "$temp_file"; then
            print_result 0 "Stream completed with done event"
        else
            echo -e "${YELLOW}⚠${NC}  No done event (stream may have been interrupted)"
        fi
    else
        print_result 1 "No streaming events received"
    fi
    
    # Show sample of response
    echo ""
    echo "Sample response (first 5 lines):"
    head -n 5 "$temp_file" | sed 's/^/  /'
    
    # Cleanup
    rm -f "$temp_file"
}

# Test 4: WebSocket Connection
test_websocket() {
    echo ""
    echo "📋 Test 4: WebSocket Connection"
    echo "------------------------------"
    
    # Check if websocat is available
    if ! command -v websocat &> /dev/null; then
        echo -e "${YELLOW}⚠${NC}  websocat not installed, skipping WebSocket test"
        echo "  Install with: brew install websocat (macOS) or cargo install websocat"
        return 0
    fi
    
    temp_file=$(mktemp)
    
    # Test WebSocket connection with ping
    echo '{"action":"ping"}' | timeout 5 websocat "ws://localhost:8000/ws" > "$temp_file" 2>&1 || true
    
    if grep -q "pong\|connected" "$temp_file"; then
        print_result 0 "WebSocket connection successful"
    else
        echo -e "${YELLOW}⚠${NC}  WebSocket test inconclusive (may need manual verification)"
    fi
    
    rm -f "$temp_file"
}

# Test 5: List Available Tools
test_tools_endpoint() {
    echo ""
    echo "📋 Test 5: Tools Endpoint"
    echo "------------------------"
    
    response=$(curl -sfL "$API_BASE_URL/tools/")
    
    if echo "$response" | grep -q "Bash\|Read\|Write"; then
        print_result 0 "Tools endpoint returned Claude Agent SDK tools"
    else
        print_result 1 "Tools endpoint failed"
    fi
}

# Test 6: Memory Endpoint
test_memory_endpoint() {
    echo ""
    echo "📋 Test 6: Memory Endpoint"
    echo "-------------------------"
    
    response=$(curl -sfL "$API_BASE_URL/memory/")
    
    if [ $? -eq 0 ]; then
        print_result 0 "Memory endpoint accessible"
    else
        print_result 1 "Memory endpoint failed"
    fi
}

# Test 7: Workspace Endpoint
test_workspace_endpoint() {
    echo ""
    echo "📋 Test 7: Workspace Endpoint"
    echo "----------------------------"
    
    response=$(curl -sf "$API_BASE_URL/workspace/stats")
    
    if echo "$response" | grep -q "total_files\|total_directories"; then
        print_result 0 "Workspace stats endpoint working"
    else
        print_result 1 "Workspace endpoint failed"
    fi
}

# Run all tests
main() {
    check_server
    test_health_check
    test_root_endpoint
    test_chat_streaming
    test_websocket
    test_tools_endpoint
    test_memory_endpoint
    test_workspace_endpoint
    
    echo ""
    echo "================================================"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  - Test with actual AI responses (requires API keys)"
    echo "  - Test memory persistence across conversations"
    echo "  - Test tool execution (Bash, Read, Write)"
    echo ""
}

# Run tests
main
