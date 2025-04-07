#!/usr/bin/env python3
"""Script to fix imports in the codebase after the agenticfleet to agentic_kernel rename."""

import os
import re
from pathlib import Path

def fix_imports(file_path: str) -> None:
    """Fix imports in a single file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the imports
    replacements = [
        ('from agentic_kernel', 'from agentic_kernel'),
        ('import agentic_kernel', 'import agentic_kernel'),
        ('from .base import BaseAgent', 'from .base import BaseAgent'),
        ('from agentic_kernel.agents.base import BaseAgent', 'from agentic_kernel.agents.base import BaseAgent'),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    # Write back only if changes were made
    with open(file_path, 'w') as f:
        f.write(content)

def main():
    """Main function to fix imports in all Python files."""
    # Get the root directory
    root_dir = Path(__file__).parent
    
    # Find all Python files
    for path in root_dir.rglob('*.py'):
        if '.venv' not in str(path):  # Skip virtual environment
            print(f"Processing {path}")
            fix_imports(str(path))

if __name__ == '__main__':
    main() 