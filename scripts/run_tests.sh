#!/bin/zsh
# Run all tests for the project using UV

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Set the project root directory
PROJECT_ROOT=$(pwd)

echo "${BLUE}Running tests with UV for AgenticFleet-Labs${NC}"

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "${YELLOW}UV not found. Installing UV package manager...${NC}"
    curl -sSf https://astral.sh/uv/install.sh | sh
    echo "${GREEN}UV installed successfully!${NC}"
fi

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "${YELLOW}Virtual environment not found. Creating one with UV...${NC}"
    uv venv .venv
fi

# Activate virtual environment
echo "${BLUE}Activating virtual environment...${NC}"
source .venv/bin/activate

# Install dependencies if needed
if [ -f "pyproject.toml" ]; then
    echo "${BLUE}Installing dependencies from pyproject.toml...${NC}"
    uv pip install -e . --quiet
elif [ -f "requirements.txt" ]; then
    echo "${BLUE}Installing dependencies from requirements.txt...${NC}"
    uv pip install -r requirements.txt --quiet
fi

# Install test dependencies
echo "${BLUE}Installing test dependencies...${NC}"
uv pip install pytest pytest-asyncio pytest-cov --quiet

# Set the PYTHONPATH
export PYTHONPATH=$PROJECT_ROOT

# Run our working tests
echo "\n${YELLOW}Running TaskManager tests...${NC}"
uv run python -m pytest tests/test_task_manager.py -v

echo "\n${YELLOW}Running TaskList synchronization tests...${NC}"
uv run python -m pytest tests/test_tasklist_sync.py -v

# Generate coverage report for our working tests
echo "\n${YELLOW}Generating coverage report for our working tests...${NC}"
uv run python -m pytest --cov=src tests/test_task_manager.py tests/test_tasklist_sync.py -v

echo "\n${GREEN}All tests completed!${NC}" 