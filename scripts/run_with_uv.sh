#!/bin/zsh
# Run Chainlit app with UV package manager

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Set the project root directory
PROJECT_ROOT=$(pwd)
APP_FILE=${1:-"src/agentic_kernel/app.py"}

echo "${BLUE}Running ${YELLOW}$APP_FILE${BLUE} with UV and Chainlit${NC}"

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
    echo "${BLUE}Checking dependencies from pyproject.toml...${NC}"
    uv pip install -e . --quiet
elif [ -f "requirements.txt" ]; then
    echo "${BLUE}Checking dependencies from requirements.txt...${NC}"
    uv pip install -r requirements.txt --quiet
fi

# Ensure chainlit is installed
if ! python -c "import chainlit" &> /dev/null; then
    echo "${YELLOW}Installing chainlit...${NC}"
    uv pip install chainlit --quiet
fi

# Set the PYTHONPATH
export PYTHONPATH=$PROJECT_ROOT

echo "${GREEN}Starting Chainlit application...${NC}"
echo "App: ${YELLOW}$APP_FILE${NC}"
echo "PYTHONPATH: ${YELLOW}$PYTHONPATH${NC}"
echo "${BLUE}Press Ctrl+C to stop the application${NC}"
echo

# Run the application with UV
uv run chainlit run $APP_FILE -w 