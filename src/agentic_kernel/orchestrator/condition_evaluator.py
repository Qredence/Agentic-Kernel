"""Condition evaluation for workflow branches.

This module provides functionality for evaluating conditional expressions in workflows,
enabling dynamic branching based on previous step results, context data,
and other runtime conditions.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Callable, Match
import operator
import ast
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """Evaluates conditional expressions for workflow branching.

    This class provides a secure way to evaluate condition strings provided in
    workflow steps, allowing for dynamic branching based on step results
    and runtime context.

    Attributes:
        context: The execution context containing variables for evaluation
        safe_functions: Dictionary of safe functions allowed in conditions
    """

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """Initialize the condition evaluator.

        Args:
            context: Initial context variables available for evaluation
        """
        self.context: Dict[str, Any] = context or {}
        
        # Define safe functions that can be used in conditions
        self.safe_functions: Dict[str, Callable] = {
            # Comparison
            "eq": operator.eq,
            "ne": operator.ne,
            "lt": operator.lt,
            "gt": operator.gt,
            "le": operator.le,
            "ge": operator.ge,
            
            # String operations
            "contains": lambda s, sub: sub in s if isinstance(s, str) else False,
            "startswith": lambda s, prefix: s.startswith(prefix) if isinstance(s, str) else False,
            "endswith": lambda s, suffix: s.endswith(suffix) if isinstance(s, str) else False,
            
            # List operations
            "in": lambda item, container: item in container if hasattr(container, "__contains__") else False,
            "not_in": lambda item, container: item not in container if hasattr(container, "__contains__") else True,
            "any": lambda items: any(items) if hasattr(items, "__iter__") else False,
            "all": lambda items: all(items) if hasattr(items, "__iter__") else False,
            "length": lambda x: len(x) if hasattr(x, "__len__") else 0,
            
            # Type checking
            "is_string": lambda x: isinstance(x, str),
            "is_number": lambda x: isinstance(x, (int, float)),
            "is_list": lambda x: isinstance(x, list),
            "is_dict": lambda x: isinstance(x, dict),
            "is_null": lambda x: x is None,
            
            # Logical operations
            "and": lambda a, b: a and b,
            "or": lambda a, b: a or b,
            "not": lambda x: not x,
            
            # Math operations
            "add": operator.add,
            "sub": operator.sub,
            "mul": operator.mul,
            "div": lambda a, b: a / b if b != 0 else None,
            "mod": lambda a, b: a % b if b != 0 else None,
        }

    def update_context(self, new_context: Dict[str, Any]) -> None:
        """Update the evaluation context with new variables.

        Args:
            new_context: Dictionary of new context variables to add/update
        """
        self.context.update(new_context)

    def evaluate(self, condition: str) -> bool:
        """Evaluate a condition expression.

        Args:
            condition: String condition to evaluate

        Returns:
            Boolean result of condition evaluation

        Raises:
            ValueError: If condition syntax is invalid or uses unsafe operations
        """
        if not condition or not condition.strip():
            return True  # Empty conditions always evaluate to true
            
        try:
            # Parse condition using special syntax for variable access
            parsed_condition = self._parse_template_vars(condition)
            
            # Create a restricted environment for evaluation
            restricted_globals = {
                "__builtins__": {},  # No built-ins allowed for security
                **self.safe_functions,  # Only explicitly allowed functions
            }
            
            # Evaluate the parsed condition in the restricted environment
            result = eval(parsed_condition, restricted_globals, self.context)
            
            # Ensure result is boolean
            if not isinstance(result, bool):
                result = bool(result)
                
            logger.debug(f"Condition '{condition}' evaluated to {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {str(e)}")
            # Return False on error, but log the issue
            return False

    def _parse_template_vars(self, text: str) -> str:
        """Parse template variables in the format ${variable.path}.

        This allows accessing nested dictionary values using dot notation.

        Args:
            text: Text containing template variables

        Returns:
            Processed text with variable references replaced
        """
        def replace_var(match: Match) -> str:
            """Replace a variable reference with its Python access code."""
            var_path = match.group(1).split('.')
            
            # Convert the dot notation to dictionary access
            if len(var_path) == 1:
                # Simple variable access
                return f"context.get('{var_path[0]}')"
            else:
                # Nested access with error handling
                root = var_path[0]
                accessors = var_path[1:]
                accessor_str = "".join(f".get('{key}', {{}})" for key in accessors)
                return f"context.get('{root}', {{}}){''.join(accessor_str)}"
                
        # Replace ${var.path} with appropriate dictionary access
        pattern = r'\${([a-zA-Z0-9_.]+)}'
        return re.sub(pattern, replace_var, text)

    def evaluate_complex_condition(self, condition_obj: Dict[str, Any]) -> bool:
        """Evaluate a complex condition object.

        This handles more complex conditions specified as dictionaries with
        operators and operands.

        Args:
            condition_obj: Dictionary specifying the condition

        Returns:
            Boolean result of condition evaluation

        Examples:
            >>> evaluator = ConditionEvaluator({"x": 5, "y": 10})
            >>> evaluator.evaluate_complex_condition({"op": "gt", "args": ["${x}", 3]})
            True
            >>> evaluator.evaluate_complex_condition({"op": "and", "args": [
            ...     {"op": "gt", "args": ["${x}", 3]},
            ...     {"op": "lt", "args": ["${y}", 20]}
            ... ]})
            True
        """
        if not condition_obj or not isinstance(condition_obj, dict):
            return True  # Empty or invalid conditions evaluate to true
            
        try:
            # Get operator and arguments
            op = condition_obj.get("op")
            args = condition_obj.get("args", [])
            
            if not op or op not in self.safe_functions:
                logger.error(f"Invalid or unsafe operator: {op}")
                return False
                
            # Process arguments recursively
            processed_args = []
            for arg in args:
                if isinstance(arg, dict) and "op" in arg:
                    # Recursively evaluate nested conditions
                    processed_args.append(self.evaluate_complex_condition(arg))
                elif isinstance(arg, str) and "${" in arg:
                    # Parse variable references
                    parsed_arg = self._parse_template_vars(arg)
                    try:
                        # Evaluate the parsed argument
                        processed_args.append(eval(parsed_arg, {"__builtins__": {}}, self.context))
                    except Exception as e:
                        logger.error(f"Error evaluating argument '{arg}': {str(e)}")
                        processed_args.append(None)
                else:
                    # Use literal value
                    processed_args.append(arg)
                    
            # Apply the operation to processed arguments
            func = self.safe_functions[op]
            result = func(*processed_args)
            
            logger.debug(f"Complex condition with operator '{op}' evaluated to {result}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error evaluating complex condition: {str(e)}")
            return False


class ConditionalBranchManager:
    """Manages conditional branching in workflows.

    This class provides functionality for determining which workflow
    branches should be executed based on step conditions and results
    from previous steps.

    Attributes:
        evaluator: ConditionEvaluator for evaluating step conditions
        execution_context: Shared context for condition evaluation
    """

    def __init__(self, initial_context: Optional[Dict[str, Any]] = None):
        """Initialize the conditional branch manager.

        Args:
            initial_context: Initial context for condition evaluation
        """
        self.execution_context: Dict[str, Any] = initial_context or {}
        self.evaluator = ConditionEvaluator(self.execution_context)

    def update_execution_context(self, updates: Dict[str, Any]) -> None:
        """Update the execution context with new data.

        Args:
            updates: Dictionary of context updates
        """
        self.execution_context.update(updates)
        self.evaluator.update_context(self.execution_context)
        
    def record_step_result(self, step_name: str, result: Dict[str, Any]) -> None:
        """Record a step execution result in the context.

        This makes the result available for condition evaluation in
        subsequent steps.

        Args:
            step_name: Name of the step
            result: Result data from step execution
        """
        # Add step result to context under step_results dictionary
        if "step_results" not in self.execution_context:
            self.execution_context["step_results"] = {}
            
        self.execution_context["step_results"][step_name] = result
        
        # Add a convenience shortcut for the result's status
        if "step_status" not in self.execution_context:
            self.execution_context["step_status"] = {}
            
        self.execution_context["step_status"][step_name] = result.get("status", "unknown")
        
        # Update the evaluator's context
        self.evaluator.update_context(self.execution_context)
        
    def should_execute_step(self, step_name: str, condition: Optional[str]) -> bool:
        """Determine if a step should be executed based on its condition.

        Args:
            step_name: Name of the step
            condition: Condition string for the step

        Returns:
            True if the step should be executed, False otherwise
        """
        if not condition:
            return True  # No condition means always execute
            
        logger.debug(f"Evaluating condition for step '{step_name}': {condition}")
        
        # Add current step name to context
        self.execution_context["current_step"] = step_name
        
        # Evaluate the condition
        try:
            result = self.evaluator.evaluate(condition)
            logger.info(f"Condition for step '{step_name}' evaluated to {result}")
            return result
        except Exception as e:
            logger.error(f"Error evaluating condition for step '{step_name}': {str(e)}")
            return False  # Fail closed on errors
            
    def should_execute_complex_step(
        self, step_name: str, condition_obj: Optional[Dict[str, Any]]
    ) -> bool:
        """Determine if a step should be executed based on a complex condition.

        Args:
            step_name: Name of the step
            condition_obj: Complex condition object for the step

        Returns:
            True if the step should be executed, False otherwise
        """
        if not condition_obj:
            return True  # No condition means always execute
            
        logger.debug(f"Evaluating complex condition for step '{step_name}'")
        
        # Add current step name to context
        self.execution_context["current_step"] = step_name
        
        # Evaluate the complex condition
        try:
            result = self.evaluator.evaluate_complex_condition(condition_obj)
            logger.info(f"Complex condition for step '{step_name}' evaluated to {result}")
            return result
        except Exception as e:
            logger.error(f"Error evaluating complex condition for step '{step_name}': {str(e)}")
            return False  # Fail closed on errors
            
    def get_ready_steps_with_conditions(
        self, workflow_id: str, steps: List[Dict[str, Any]], completed_steps: List[str]
    ) -> List[str]:
        """Get workflow steps that are ready to execute, considering conditions.

        Args:
            workflow_id: ID of the workflow
            steps: List of workflow steps
            completed_steps: List of completed step names

        Returns:
            List of step names that are ready to execute
        """
        ready_steps = []
        
        # Add workflow ID to context
        self.execution_context["workflow_id"] = workflow_id
        
        for step in steps:
            step_name = step.get("name", "")
            
            # Skip completed steps
            if step_name in completed_steps:
                continue
                
            # Check if dependencies are satisfied
            dependencies = step.get("dependencies", [])
            deps_completed = all(dep in completed_steps for dep in dependencies)
            
            if not deps_completed:
                continue
                
            # Check if condition is satisfied
            condition = step.get("condition")
            if condition:
                condition_result = (
                    self.should_execute_complex_step(step_name, condition)
                    if isinstance(condition, dict)
                    else self.should_execute_step(step_name, condition)
                )
                
                if not condition_result:
                    # Mark this step as "skipped" in the context
                    if "step_status" not in self.execution_context:
                        self.execution_context["step_status"] = {}
                    self.execution_context["step_status"][step_name] = "skipped"
                    
                    # Add to "skipped_steps" list
                    if "skipped_steps" not in self.execution_context:
                        self.execution_context["skipped_steps"] = []
                    if step_name not in self.execution_context["skipped_steps"]:
                        self.execution_context["skipped_steps"].append(step_name)
                        
                    continue
                    
            # Step is ready to execute
            ready_steps.append(step_name)
            
        return ready_steps 