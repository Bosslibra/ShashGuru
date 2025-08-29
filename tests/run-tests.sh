#!/bin/bash

# ShashGuru Test Runner Script
# This script provides convenient commands for running different types of tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the tests directory
if [[ ! -f "package.json" ]]; then
    print_error "Please run this script from the tests directory"
    exit 1
fi

# Function to check if dependencies are installed
check_dependencies() {
    if [[ ! -d "node_modules" ]]; then
        print_warning "Dependencies not found. Installing..."
        npm install
    fi
    
    if [[ ! -d "node_modules/@playwright" ]]; then
        print_warning "Playwright browsers not found. Installing..."
        npx playwright install
    fi
}

# Function to run tests with different configurations
run_tests() {
    local mode=$1
    local browser=$2
    local test_file=$3
    
    print_status "Running tests in $mode mode..."
    
    case $mode in
        "all")
            npx playwright test
            ;;
        "headed")
            npx playwright test --headed
            ;;
        "debug")
            npx playwright test --debug
            ;;
        "ui")
            npx playwright test --ui
            ;;
        "browser")
            npx playwright test --project=$browser
            ;;
        "file")
            npx playwright test $test_file
            ;;
        "accessibility")
            npx playwright test tests/01-accessibility.spec.js
            ;;
        "chess")
            npx playwright test tests/02-chess-board.spec.js
            ;;
        "ai")
            npx playwright test tests/03-ai-chat.spec.js
            ;;
        "pgn")
            npx playwright test tests/04-pgn-upload.spec.js
            ;;
        "live")
            npx playwright test tests/05-live-section.spec.js
            ;;
        *)
            print_error "Unknown test mode: $mode"
            exit 1
            ;;
    esac
}

# Function to show test results
show_results() {
    if [[ -f "playwright-report/index.html" ]]; then
        print_success "Test report generated: playwright-report/index.html"
        
        # Try to open the report in browser (if available)
        if command -v xdg-open &> /dev/null; then
            print_status "Opening test report in browser..."
            xdg-open playwright-report/index.html
        elif command -v open &> /dev/null; then
            print_status "Opening test report in browser..."
            open playwright-report/index.html
        fi
    fi
}

# Function to clean up test artifacts
cleanup() {
    print_status "Cleaning up test artifacts..."
    rm -rf test-results/
    rm -rf playwright-report/
    rm -rf temp/
    print_success "Cleanup completed"
}

# Help function
show_help() {
    echo "ShashGuru Test Runner"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  install              Install dependencies and Playwright browsers"
    echo "  test                 Run all tests"
    echo "  test:headed          Run tests in headed mode (visible browser)"
    echo "  test:debug           Run tests in debug mode"
    echo "  test:ui              Run tests with UI (interactive mode)"
    echo "  test:accessibility   Run only accessibility tests"
    echo "  test:chess           Run only chess board tests"
    echo "  test:ai              Run only AI chat tests"
    echo "  test:pgn             Run only PGN upload tests"
    echo "  test:live            Run only live section tests"
    echo "  test:chromium        Run tests in Chromium only"
    echo "  test:firefox         Run tests in Firefox only"
    echo "  test:webkit          Run tests in WebKit only"
    echo "  report               Show test report (if exists)"
    echo "  cleanup              Clean up test artifacts"
    echo "  help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 install"
    echo "  $0 test"
    echo "  $0 test:headed"
    echo "  $0 test:accessibility"
    echo "  $0 test:chromium"
    echo ""
}

# Main script logic
case ${1:-help} in
    "install")
        print_status "Installing dependencies..."
        npm install
        print_status "Installing Playwright browsers..."
        npx playwright install
        print_success "Installation completed"
        ;;
    "test")
        check_dependencies
        run_tests "all"
        show_results
        ;;
    "test:headed")
        check_dependencies
        run_tests "headed"
        show_results
        ;;
    "test:debug")
        check_dependencies
        run_tests "debug"
        ;;
    "test:ui")
        check_dependencies
        run_tests "ui"
        ;;
    "test:accessibility")
        check_dependencies
        run_tests "accessibility"
        show_results
        ;;
    "test:chess")
        check_dependencies
        run_tests "chess"
        show_results
        ;;
    "test:ai")
        check_dependencies
        run_tests "ai"
        show_results
        ;;
    "test:pgn")
        check_dependencies
        run_tests "pgn"
        show_results
        ;;
    "test:live")
        check_dependencies
        run_tests "live"
        show_results
        ;;
    "test:chromium")
        check_dependencies
        run_tests "browser" "chromium"
        show_results
        ;;
    "test:firefox")
        check_dependencies
        run_tests "browser" "firefox"
        show_results
        ;;
    "test:webkit")
        check_dependencies
        run_tests "browser" "webkit"
        show_results
        ;;
    "report")
        show_results
        ;;
    "cleanup")
        cleanup
        ;;
    "help")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
