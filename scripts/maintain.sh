#!/bin/bash
# Script to maintain the codebase by performing cleanup and organization tasks

set -e  # Exit on error

echo "Maintaining codebase..."

# Function to clean up Python cache files
cleanup_python_cache() {
    echo "Removing Python cache files..."
    find . -type d -name "__pycache__" -exec rm -rf {} \; 2>/dev/null || true
    find . -name "*.pyc" -delete
    find . -name "*.pyo" -delete
    find . -name "*.pyd" -delete
    find . -name ".pytest_cache" -exec rm -rf {} \; 2>/dev/null || true
    echo "Python cache cleanup complete."
}

# Function to check for duplicate files
check_duplicates() {
    echo "Checking for potential duplicate files..."
    python check_duplicates.py
}

# Function to format Python code
format_code() {
    echo "Formatting Python code..."
    python -m black src tests examples || echo "Black formatting failed, make sure it's installed"
    python -m isort src tests examples || echo "Isort formatting failed, make sure it's installed"
    echo "Code formatting complete."
}

# Function to run tests
run_tests() {
    echo "Running tests..."
    python -m pytest || echo "Tests failed!"
}

# Main menu
case "$1" in
    clean)
        cleanup_python_cache
        ;;
    duplicates)
        check_duplicates
        ;;
    format)
        format_code
        ;;
    test)
        run_tests
        ;;
    all)
        cleanup_python_cache
        check_duplicates
        format_code
        run_tests
        ;;
    *)
        echo "Usage: $0 {clean|duplicates|format|test|all}"
        echo "  clean      - Remove Python cache and temporary files"
        echo "  duplicates - Check for potential duplicate files"
        echo "  format     - Format Python code using black and isort"
        echo "  test       - Run tests"
        echo "  all        - Run all maintenance tasks"
        exit 1
esac

echo "Maintenance completed."
exit 0 