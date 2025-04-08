#!/usr/bin/env python3
"""
Script to run the agentic_kernel tests using uv package manager and the virtual environment.
This avoids issues with semantic_kernel dependencies and environment conflicts.
"""
import os
import sys
import subprocess
import argparse


def ensure_venv():
    """Ensure we're running in the virtual environment."""
    venv_path = os.path.join(os.getcwd(), ".venv")
    if not os.path.exists(venv_path):
        print("Creating virtual environment with uv...")
        subprocess.run(["uv", "venv"], check=True)
    
    # Check if we're already in the venv
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv:
        print("Please run this script within the virtual environment.")
        print(f"Activate it with: source {os.path.join(venv_path, 'bin', 'activate')}")
        sys.exit(1)


def install_dependencies():
    """Install required dependencies using uv."""
    print("Installing dependencies with uv...")
    subprocess.run(["uv", "pip", "install", "-e", "."], check=True)


def run_tests(test_path):
    """Run the specified tests."""
    print(f"Running tests: {test_path}")
    result = subprocess.run(["python", "-m", "pytest", test_path, "-v"], check=False)
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run agentic_kernel tests")
    parser.add_argument("test_path", nargs='?', default="tests/test_complex_agent_workflows.py",
                      help="Path to the test file or directory (default: tests/test_complex_agent_workflows.py)")
    args = parser.parse_args()
    
    # Make sure we're in the venv
    ensure_venv()
    
    # Install dependencies
    install_dependencies()
    
    # Run the tests
    exit_code = run_tests(args.test_path)
    
    # Exit with the test result code
    sys.exit(exit_code) 