import pytest
import sys

def main():
    """Run the specified test file."""
    try:
        print("Running tests for conditional branching...")
        result_conditional = pytest.main(['tests/test_condition_evaluator.py', '-v'])
        print(f"Conditional branching test result code: {result_conditional}")
        
        print("Running tests for workflow optimizer...")
        result_optimizer = pytest.main(['tests/test_workflow_optimizer.py', '-v'])
        print(f"Workflow optimizer test result code: {result_optimizer}")
        
        # Return failure if any test failed
        return 1 if result_conditional != 0 or result_optimizer != 0 else 0
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 