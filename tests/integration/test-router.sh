#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ROUTER_URL="${ROUTER_URL:-http://localhost:3000}"
TIMEOUT=30

echo "🧪 Claude Code Router - Integration Tests"
echo "=========================================="
echo ""
echo "Testing Router at: $ROUTER_URL"
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

# Function to check if router is running
check_router() {
    echo "🔍 Checking if Claude Code Router is running..."
    if curl -sf "$ROUTER_URL/health" > /dev/null 2>&1; then
        print_result 0 "Router is healthy"
        return 0
    else
        echo -e "${RED}✗${NC} Router is not responding at $ROUTER_URL"
        echo "Please start the server with: docker-compose up -d"
        exit 1
    fi
}

# Test 1: Router Health Check
test_router_health() {
    echo ""
    echo "📋 Test 1: Router Health Check"
    echo "-----------------------------"
    
    response=$(curl -sf "$ROUTER_URL/health" 2>&1)
    
    if [ $? -eq 0 ]; then
        print_result 0 "Router health endpoint accessible"
    else
        print_result 1 "Router health check failed"
    fi
}

# Test 2: Router Configuration
test_router_config() {
    echo ""
    echo "📋 Test 2: Router Configuration"
    echo "------------------------------"
    
    # Check if config file exists in container
    if docker exec ai-companion-server test -f /root/.claude-code-router/config.json; then
        print_result 0 "Router configuration file exists"
        
        # Validate JSON
        if docker exec ai-companion-server cat /root/.claude-code-router/config.json | python3 -m json.tool > /dev/null 2>&1; then
            print_result 0 "Router configuration is valid JSON"
        else
            print_result 1 "Router configuration is invalid JSON"
        fi
    else
        print_result 1 "Router configuration file not found"
    fi
}

# Test 3: Check Router Providers
test_router_providers() {
    echo ""
    echo "📋 Test 3: Router Providers Configuration"
    echo "----------------------------------------"
    
    config=$(docker exec ai-companion-server cat /root/.claude-code-router/config.json 2>/dev/null)
    
    if echo "$config" | grep -q "anthropic"; then
        print_result 0 "Anthropic provider configured"
    else
        echo -e "${YELLOW}⚠${NC}  Anthropic provider not found"
    fi
    
    if echo "$config" | grep -q "openrouter"; then
        print_result 0 "OpenRouter provider configured"
    else
        echo -e "${YELLOW}⚠${NC}  OpenRouter provider not found"
    fi
    
    if echo "$config" | grep -q "ollama"; then
        print_result 0 "Ollama provider configured"
    else
        echo -e "${YELLOW}⚠${NC}  Ollama provider not found"
    fi
    
    if echo "$config" | grep -q "local-companion"; then
        print_result 0 "Local companion provider configured"
    else
        echo -e "${YELLOW}⚠${NC}  Local companion provider not found"
    fi
}

# Test 4: Check Router Routes
test_router_routes() {
    echo ""
    echo "📋 Test 4: Router Routes Configuration"
    echo "-------------------------------------"
    
    config=$(docker exec ai-companion-server cat /root/.claude-code-router/config.json 2>/dev/null)
    
    if echo "$config" | grep -q '"default"'; then
        print_result 0 "Default route configured"
    else
        print_result 1 "Default route not configured"
    fi
    
    if echo "$config" | grep -q '"background"'; then
        print_result 0 "Background route configured"
    else
        echo -e "${YELLOW}⚠${NC}  Background route not configured"
    fi
    
    if echo "$config" | grep -q '"think"'; then
        print_result 0 "Think route configured"
    else
        echo -e "${YELLOW}⚠${NC}  Think route not configured"
    fi
}

# Test 5: Check Both Services Running
test_both_services() {
    echo ""
    echo "📋 Test 5: Both Services Running in Container"
    echo "--------------------------------------------"
    
    # Check if FastAPI is running
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        print_result 0 "FastAPI server is running (port 8000)"
    else
        print_result 1 "FastAPI server is not running"
    fi
    
    # Check if Router is running
    if curl -sf http://localhost:3000/health > /dev/null 2>&1; then
        print_result 0 "Claude Code Router is running (port 3000)"
    else
        print_result 1 "Claude Code Router is not running"
    fi
}

# Test 6: Check Router Logs
test_router_logs() {
    echo ""
    echo "📋 Test 6: Router Logs"
    echo "---------------------"
    
    if docker exec ai-companion-server test -d /root/.claude-code-router/logs; then
        print_result 0 "Router logs directory exists"
        
        log_count=$(docker exec ai-companion-server sh -c "ls -1 /root/.claude-code-router/logs/*.log 2>/dev/null | wc -l" || echo "0")
        
        if [ "$log_count" -gt 0 ]; then
            print_result 0 "Router log files present ($log_count files)"
        else
            echo -e "${YELLOW}⚠${NC}  No log files yet (may be normal if just started)"
        fi
    else
        echo -e "${YELLOW}⚠${NC}  Router logs directory not found"
    fi
}

# Test 7: Environment Variables
test_environment_vars() {
    echo ""
    echo "📋 Test 7: Environment Variables"
    echo "-------------------------------"
    
    # Check if ANTHROPIC_API_KEY is set
    if docker exec ai-companion-server sh -c 'test -n "$ANTHROPIC_API_KEY"' 2>/dev/null; then
        print_result 0 "ANTHROPIC_API_KEY is set"
    else
        echo -e "${YELLOW}⚠${NC}  ANTHROPIC_API_KEY not set (required for router)"
    fi
    
    # Check if ROUTER_API_KEY is set
    if docker exec ai-companion-server sh -c 'test -n "$ROUTER_API_KEY"' 2>/dev/null; then
        print_result 0 "ROUTER_API_KEY is set"
    else
        echo -e "${YELLOW}⚠${NC}  ROUTER_API_KEY not set"
    fi
}

# Run all tests
main() {
    check_router
    test_router_health
    test_router_config
    test_router_providers
    test_router_routes
    test_both_services
    test_router_logs
    test_environment_vars
    
    echo ""
    echo "=========================================="
    echo -e "${GREEN}✓ All router tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  - Connect Claude Code CLI: ccr activate http://localhost:3000 \$ROUTER_API_KEY"
    echo "  - Test model switching: /model"
    echo "  - Test routing to different providers"
    echo ""
}

# Run tests
main
