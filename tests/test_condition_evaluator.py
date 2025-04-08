"""Tests for the conditional branching functionality in workflows."""

import pytest
from typing import Dict, Any, List
import os
import json

from src.agentic_kernel.orchestrator.condition_evaluator import (
    ConditionEvaluator,
    ConditionalBranchManager,
)


def test_condition_evaluator_simple_conditions():
    """Test that the condition evaluator handles simple conditions correctly."""
    # Setup
    context = {"x": 5, "y": "test", "z": [1, 2, 3]}
    evaluator = ConditionEvaluator(context)
    
    # Test simple conditions
    assert evaluator.evaluate("eq(${x}, 5)")
    assert not evaluator.evaluate("eq(${x}, 10)")
    assert evaluator.evaluate("gt(${x}, 3)")
    assert evaluator.evaluate("contains(${y}, 'es')")
    assert evaluator.evaluate("length(${z}) == 3")
    
    # Test logical operations
    assert evaluator.evaluate("and(gt(${x}, 3), eq(length(${z}), 3))")
    assert evaluator.evaluate("or(lt(${x}, 3), contains(${y}, 'es'))")
    assert evaluator.evaluate("not(eq(${x}, 10))")


def test_condition_evaluator_complex_conditions():
    """Test that the condition evaluator handles complex nested conditions."""
    # Setup
    context = {
        "data": {
            "values": [10, 20, 30],
            "metadata": {"owner": "test_user", "created": "2023-01-01"},
        },
        "flags": {"debug": True, "verbose": False},
    }
    evaluator = ConditionEvaluator(context)
    
    # Test nested access
    assert evaluator.evaluate("eq(${data.metadata.owner}, 'test_user')")
    assert evaluator.evaluate("in(20, ${data.values})")
    assert evaluator.evaluate("${flags.debug}")
    assert not evaluator.evaluate("${flags.verbose}")
    
    # Test complex expressions
    assert evaluator.evaluate(
        "and(contains(${data.metadata.owner}, 'user'), gt(length(${data.values}), 2))"
    )


def test_condition_evaluator_invalid_conditions():
    """Test how the condition evaluator handles invalid or unsafe conditions."""
    # Setup
    context = {"x": 5, "y": "test"}
    evaluator = ConditionEvaluator(context)
    
    # Test empty conditions (should default to True)
    assert evaluator.evaluate("")
    assert evaluator.evaluate(None)
    
    # Test invalid syntax
    assert not evaluator.evaluate("invalid syntax")
    
    # Test undefined variables (should not crash)
    assert not evaluator.evaluate("eq(${unknown}, 10)")
    
    # Test attempt to use unsafe functions (should not execute)
    # This tests the security of the evaluator
    assert not evaluator.evaluate("__import__('os').system('echo SECURITY_BREACH')")


def test_condition_evaluator_complex_object():
    """Test that the condition evaluator can handle complex dictionary conditions."""
    # Setup
    context = {"x": 5, "y": 10, "values": [1, 2, 3]}
    evaluator = ConditionEvaluator(context)
    
    # Test simple complex condition
    simple_condition = {"op": "gt", "args": ["${x}", 3]}
    assert evaluator.evaluate_complex_condition(simple_condition)
    
    # Test nested complex condition
    nested_condition = {
        "op": "and",
        "args": [
            {"op": "gt", "args": ["${x}", 3]},
            {"op": "lt", "args": ["${y}", 20]},
        ],
    }
    assert evaluator.evaluate_complex_condition(nested_condition)
    
    # Test with list operations
    list_condition = {
        "op": "all",
        "args": [
            [
                {"op": "in", "args": [1, "${values}"]},
                {"op": "in", "args": [2, "${values}"]},
                {"op": "in", "args": [3, "${values}"]},
            ]
        ],
    }
    assert evaluator.evaluate_complex_condition(list_condition)


def test_conditional_branch_manager_basics():
    """Test basic functionality of the conditional branch manager."""
    # Setup
    manager = ConditionalBranchManager()
    
    # Test initial state
    assert manager.execution_context == {}
    
    # Test context updates
    manager.update_execution_context({"workflow_id": "test123", "step_count": 5})
    assert manager.execution_context["workflow_id"] == "test123"
    assert manager.execution_context["step_count"] == 5
    
    # Test recording step results
    manager.record_step_result("step1", {"status": "success", "output": "result1"})
    assert "step_results" in manager.execution_context
    assert manager.execution_context["step_results"]["step1"]["status"] == "success"
    assert manager.execution_context["step_status"]["step1"] == "success"


def test_conditional_branch_manager_step_execution():
    """Test that the branch manager correctly determines which steps to execute."""
    # Setup
    manager = ConditionalBranchManager()
    
    # Setup initial context with some step results
    manager.record_step_result("step1", {"status": "success", "data": {"value": 10}})
    manager.record_step_result("step2", {"status": "failed", "error": "Test error"})
    
    # Test conditions that should evaluate to true
    assert manager.should_execute_step(
        "step3", "eq(${step_status.step1}, 'success')"
    )
    assert manager.should_execute_step(
        "step3", "gt(${step_results.step1.data.value}, 5)"
    )
    
    # Test conditions that should evaluate to false
    assert not manager.should_execute_step(
        "step4", "eq(${step_status.step2}, 'success')"
    )
    assert not manager.should_execute_step(
        "step4", "lt(${step_results.step1.data.value}, 5)"
    )
    
    # Test complex conditions
    complex_condition = {
        "op": "and",
        "args": [
            {"op": "eq", "args": ["${step_status.step1}", "success"]},
            {"op": "eq", "args": ["${step_status.step2}", "failed"]},
        ],
    }
    assert manager.should_execute_complex_step("step5", complex_condition)


def test_ready_steps_with_conditions():
    """Test that the branch manager correctly identifies ready steps considering conditions."""
    # Setup
    manager = ConditionalBranchManager()
    
    # Add some completed steps
    completed_steps = ["step1", "step2"]
    
    # Define a workflow with conditional steps
    workflow_steps = [
        {
            "name": "step1",
            "dependencies": [],
        },
        {
            "name": "step2",
            "dependencies": ["step1"],
        },
        {
            "name": "step3",
            "dependencies": ["step2"],
            "condition": "true",  # This should execute
        },
        {
            "name": "step4",
            "dependencies": ["step2"],
            "condition": "false",  # This should be skipped
        },
        {
            "name": "step5",
            "dependencies": ["step3"],  # This shouldn't be ready yet
        },
    ]
    
    # Test getting ready steps
    ready_steps = manager.get_ready_steps_with_conditions("test_workflow", workflow_steps, completed_steps)
    
    # step3 should be ready, step4 should be skipped, step5 should not be ready
    assert "step3" in ready_steps
    assert "step4" not in ready_steps
    assert "step5" not in ready_steps
    
    # Check that step4 was marked as skipped
    assert manager.execution_context["step_status"]["step4"] == "skipped"
    assert "step4" in manager.execution_context["skipped_steps"]


def test_condition_evaluator_context_isolation():
    """Test that the condition evaluator properly isolates execution context."""
    # Setup 
    evaluator = ConditionEvaluator({"x": 5})
    
    # Test that we can't access Python builtins or modules
    # This is a security check
    assert not evaluator.evaluate("__builtins__")
    assert not evaluator.evaluate("__import__")
    assert not evaluator.evaluate("open")
    
    # Test that we can't modify the context through eval
    assert not evaluator.evaluate("context.update({'hacked': True})")
    assert not evaluator.evaluate("context.clear()")
    assert "hacked" not in evaluator.context


def test_template_var_parsing():
    """Test the template variable parsing functionality."""
    # Setup
    context = {
        "values": {"a": 1, "b": 2},
        "nested": {"level1": {"level2": {"value": "test"}}},
    }
    evaluator = ConditionEvaluator(context)
    
    # Test parsing and evaluation
    assert evaluator.evaluate("eq(${values.a}, 1)")
    assert evaluator.evaluate("eq(${nested.level1.level2.value}, 'test')")
    
    # Test non-existent values (should not raise error)
    assert not evaluator.evaluate("eq(${values.missing}, 1)")
    assert not evaluator.evaluate("eq(${missing.path}, 1)")
    
    # Test nested reference in string
    assert evaluator.evaluate("contains('The value is ${nested.level1.level2.value}', 'test')") 