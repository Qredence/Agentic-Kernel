#!/usr/bin/env python3
"""Run tests for the project."""

import os
import sys
import subprocess

# Set up paths
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.environ["PYTHONPATH"] = project_root

# Set up virtual environment python
if os.path.exists(".venv/bin/python"):
    python_path = os.path.join(project_root, ".venv/bin/python")
elif os.path.exists(".venv/Scripts/python.exe"):  # Windows
    python_path = os.path.join(project_root, ".venv/Scripts/python.exe")
else:
    python_path = sys.executable

print(f"Using Python: {python_path}")
print(f"Project root: {project_root}")

# Run the tests
tests = [
    "tests/test_task_manager.py",
    "tests/test_tasklist_sync.py"
]

for test_file in tests:
    print(f"\n\n==== Running {test_file} ====\n")
    test_path = os.path.join(project_root, test_file)
    result = subprocess.run(
        [python_path, "-m", "pytest", test_path, "-v"],
        env={"PYTHONPATH": project_root}
    )
    if result.returncode != 0:
        print(f"Test failed: {test_file}")
        sys.exit(1)

print("\n\nAll tests passed!") 