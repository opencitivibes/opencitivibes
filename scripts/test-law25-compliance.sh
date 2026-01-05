#!/bin/bash
# Law 25 Compliance Test Script
# Tests backend API endpoints for Quebec Law 25 compliance

# Don't exit on error - we want to report all test results
# set -e

# Configuration
API_BASE="${API_BASE:-http://localhost:8000/api}"
TEST_EMAIL="law25test$(date +%s)@test.com"
TEST_PASSWORD="TestPassword123!"  # pragma: allowlist secret
TEST_USERNAME="law25test$(date +%s)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0
SKIPPED=0

# Helper functions
print_header() {
    echo ""
    echo "=============================================="
    echo -e "${YELLOW}$1${NC}"
    echo "=============================================="
}

print_test() {
    echo -n "  Testing: $1... "
}

print_pass() {
    echo -e "${GREEN}PASSED${NC}"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}FAILED${NC} - $1"
    ((FAILED++))
}

print_skip() {
    echo -e "${YELLOW}SKIPPED${NC} - $1"
    ((SKIPPED++))
}

# Check if API is running
print_header "Checking API availability"
print_test "API health check"
if curl -s "${API_BASE}/config/public" > /dev/null 2>&1; then
    print_pass
else
    print_fail "API not running at ${API_BASE}"
    echo "Please start the backend server first: cd backend && uvicorn main:app --reload"
    exit 1
fi

# ============================================================================
# PHASE 1: CONSENT MANAGEMENT
# ============================================================================
print_header "Phase 1: Consent Management"

# Test 1.1: Registration requires consent fields
print_test "Registration without consent fields fails"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"${TEST_EMAIL}\",
        \"username\": \"${TEST_USERNAME}\",
        \"display_name\": \"Test User\",
        \"password\": \"${TEST_PASSWORD}\"
    }" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "422" ]; then
    print_pass
else
    print_fail "Expected 422, got $HTTP_CODE"
fi

# Test 1.2: Registration with consent fields succeeds
print_test "Registration with consent fields succeeds"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"${TEST_EMAIL}\",
        \"username\": \"${TEST_USERNAME}\",
        \"display_name\": \"Law 25 Test User\",
        \"password\": \"${TEST_PASSWORD}\",
        \"accepts_terms\": true,
        \"accepts_privacy_policy\": true,
        \"marketing_consent\": false
    }" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    print_pass
    USER_ID=$(echo "$BODY" | grep -o '"id":[0-9]*' | cut -d':' -f2)
else
    print_fail "Expected 200/201, got $HTTP_CODE: $BODY"
fi

# Test 1.3: Login to get token
print_test "Login with new account"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${TEST_EMAIL}&password=${TEST_PASSWORD}" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    TOKEN=$(echo "$BODY" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$TOKEN" ]; then
        print_pass
    else
        print_fail "No token in response"
    fi
else
    print_fail "Expected 200, got $HTTP_CODE"
    exit 1
fi

# Test 1.4: Get consent status
print_test "Get consent status endpoint"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/auth/consent" \
    -H "Authorization: Bearer ${TOKEN}" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    # Check consent fields are present
    if echo "$BODY" | grep -q '"terms_accepted":true' && echo "$BODY" | grep -q '"privacy_accepted":true'; then
        print_pass
    else
        print_fail "Consent fields not properly set: $BODY"
    fi
else
    print_fail "Expected 200, got $HTTP_CODE"
fi

# Test 1.5: Update marketing consent
print_test "Update marketing consent"
RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/auth/consent" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"marketing_consent": true}' 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    if echo "$BODY" | grep -q '"marketing_consent":true'; then
        print_pass
    else
        print_fail "Marketing consent not updated"
    fi
else
    print_fail "Expected 200, got $HTTP_CODE"
fi

# Test 1.6: Withdraw marketing consent
print_test "Withdraw marketing consent"
RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/auth/consent" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"marketing_consent": false}' 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    if echo "$BODY" | grep -q '"marketing_consent":false'; then
        print_pass
    else
        print_fail "Marketing consent not withdrawn"
    fi
else
    print_fail "Expected 200, got $HTTP_CODE"
fi

# Test 1.7: Get consent history
print_test "Get consent history endpoint"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/auth/consent/history" \
    -H "Authorization: Bearer ${TOKEN}" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    # Check history contains expected consent entries
    if echo "$BODY" | grep -q '"consent_type"' && echo "$BODY" | grep -q '"action"'; then
        print_pass
    else
        print_fail "Consent history missing expected fields"
    fi
else
    print_fail "Expected 200, got $HTTP_CODE"
fi

# ============================================================================
# PHASE 2: DATA SUBJECT RIGHTS
# ============================================================================
print_header "Phase 2: Data Subject Rights"

# Test 2.1: Data export (JSON)
print_test "Data export endpoint (JSON)"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/auth/export-data?format=json" \
    -H "Authorization: Bearer ${TOKEN}" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    # Check export contains expected sections
    if echo "$BODY" | grep -q '"user_profile"' && echo "$BODY" | grep -q '"consent_history"'; then
        print_pass
    else
        print_fail "Export missing expected fields"
    fi
else
    print_fail "Expected 200, got $HTTP_CODE"
fi

# Test 2.2: Data export (CSV)
print_test "Data export endpoint (CSV)"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/auth/export-data?format=csv" \
    -H "Authorization: Bearer ${TOKEN}" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    print_pass
else
    print_fail "Expected 200, got $HTTP_CODE"
fi

# ============================================================================
# PHASE 4: PRIVACY SETTINGS
# ============================================================================
print_header "Phase 4: Privacy Settings"

# Test 4.1: Check reconsent endpoint
print_test "Check reconsent required endpoint"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/auth/policy/reconsent-check" \
    -H "Authorization: Bearer ${TOKEN}" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    if echo "$BODY" | grep -q '"requires_privacy_reconsent"' && echo "$BODY" | grep -q '"requires_terms_reconsent"'; then
        print_pass
    else
        print_fail "Missing reconsent fields: $BODY"
    fi
else
    print_fail "Expected 200, got $HTTP_CODE"
fi

# Test 4.2: Get policy changelog
print_test "Policy changelog endpoint"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/auth/policy/changelog/terms" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    print_pass
else
    print_fail "Expected 200, got $HTTP_CODE"
fi

# ============================================================================
# PHASE 2 (continued): ACCOUNT DELETION
# ============================================================================
print_header "Phase 2 (continued): Account Deletion"

# Test: Delete account endpoint exists
print_test "Delete account endpoint"
RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/auth/account" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"password\": \"${TEST_PASSWORD}\",
        \"confirmation_text\": \"DELETE MY ACCOUNT\",
        \"delete_content\": false
    }" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    print_pass
    echo "    Account deleted successfully"
else
    print_fail "Expected 200, got $HTTP_CODE: $BODY"
fi

# ============================================================================
# SUMMARY
# ============================================================================
print_header "Test Summary"
echo ""
echo -e "  ${GREEN}Passed:${NC}  $PASSED"
echo -e "  ${RED}Failed:${NC}  $FAILED"
echo -e "  ${YELLOW}Skipped:${NC} $SKIPPED"
echo ""

TOTAL=$((PASSED + FAILED))
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All $TOTAL tests passed!${NC}"
    exit 0
else
    echo -e "${RED}$FAILED of $TOTAL tests failed${NC}"
    exit 1
fi
