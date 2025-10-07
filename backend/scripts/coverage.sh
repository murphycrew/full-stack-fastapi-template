#!/bin/bash

# Coverage testing script for local development
# This script provides various coverage testing options

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[COVERAGE]${NC} $1"
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

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  run              Run full coverage test suite"
    echo "  html             Generate HTML coverage report and open it"
    echo "  term             Show coverage in terminal only"
    echo "  specific FILE    Run coverage for specific file (e.g., 'app/initial_data.py')"
    echo "  missing          Show only files with missing coverage"
    echo "  clean            Clean coverage cache and HTML reports"
    echo "  help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 run           # Run full coverage suite"
    echo "  $0 html          # Generate and open HTML report"
    echo "  $0 specific app/initial_data.py  # Coverage for specific file"
    echo "  $0 missing       # Show files with missing coverage"
}

# Function to activate virtual environment
activate_venv() {
    if [ -f ".venv/bin/activate" ]; then
        print_status "Activating virtual environment..."
        source .venv/bin/activate
    else
        print_error "Virtual environment not found at .venv/bin/activate"
        print_status "Please ensure you're in the backend directory and have run 'uv sync'"
        exit 1
    fi
}

# Function to run full coverage
run_full_coverage() {
    print_status "Running full coverage test suite..."
    python -m pytest --cov=app --cov-report=term-missing --cov-report=html -q
    print_success "Coverage test completed. HTML report generated in htmlcov/"
}

# Function to generate HTML report and open it
generate_html_report() {
    print_status "Generating HTML coverage report..."
    python -m pytest --cov=app --cov-report=html -q

    if [ -f "htmlcov/index.html" ]; then
        print_success "HTML report generated at htmlcov/index.html"
        print_status "Opening HTML report in browser..."

        # Try to open in browser (works on macOS, Linux with xdg-open, Windows with start)
        if command -v open >/dev/null 2>&1; then
            open htmlcov/index.html
        elif command -v xdg-open >/dev/null 2>&1; then
            xdg-open htmlcov/index.html
        elif command -v start >/dev/null 2>&1; then
            start htmlcov/index.html
        else
            print_warning "Could not automatically open browser. Please open htmlcov/index.html manually."
        fi
    else
        print_error "HTML report not generated"
        exit 1
    fi
}

# Function to show terminal-only coverage
show_terminal_coverage() {
    print_status "Running coverage test (terminal output only)..."
    python -m pytest --cov=app --cov-report=term-missing -q
}

# Function to run coverage for specific file
run_specific_coverage() {
    local file_path="$1"
    if [ -z "$file_path" ]; then
        print_error "Please specify a file path"
        echo "Example: $0 specific app/initial_data.py"
        exit 1
    fi

    if [ ! -f "$file_path" ]; then
        print_error "File not found: $file_path"
        exit 1
    fi

    print_status "Running coverage for $file_path..."
    python -m pytest --cov="$file_path" --cov-report=term-missing -q
}

# Function to show missing coverage
show_missing_coverage() {
    print_status "Running coverage test to identify missing coverage..."
    python -m pytest --cov=app --cov-report=term-missing -q | grep -E "(Name|Stmts|Missing|TOTAL)" | head -20

    print_status "Files with missing coverage:"
    python -m pytest --cov=app --cov-report=term-missing -q | grep -v "100%" | grep -E "^app/" | head -10
}

# Function to clean coverage cache
clean_coverage() {
    print_status "Cleaning coverage cache and HTML reports..."

    # Remove coverage cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name ".coverage*" -delete 2>/dev/null || true

    # Remove HTML reports
    rm -rf htmlcov/ 2>/dev/null || true
    rm -rf .coverage 2>/dev/null || true

    print_success "Coverage cache cleaned"
}

# Main script logic
main() {
    # Check if we're in the backend directory
    if [ ! -f "pyproject.toml" ] || [ ! -d "app" ]; then
        print_error "Please run this script from the backend directory"
        exit 1
    fi

    # Activate virtual environment
    activate_venv

    # Parse command line arguments
    case "${1:-help}" in
        "run")
            run_full_coverage
            ;;
        "html")
            generate_html_report
            ;;
        "term")
            show_terminal_coverage
            ;;
        "specific")
            run_specific_coverage "$2"
            ;;
        "missing")
            show_missing_coverage
            ;;
        "clean")
            clean_coverage
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown option: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
