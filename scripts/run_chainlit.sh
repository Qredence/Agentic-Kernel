#!/bin/zsh
# This script runs a Chainlit app with the correct environment setup

# Activate the virtual environment
source .venv/bin/activate

# Set the PYTHONPATH to include the current directory
export PYTHONPATH=$(pwd)

# Run the specified app or default to the main app
APP_FILE=${1:-src/agentic_kernel/app.py}

# Run the Chainlit app with debug mode (-d) and watch mode (-w)
chainlit run $APP_FILE -d -w 