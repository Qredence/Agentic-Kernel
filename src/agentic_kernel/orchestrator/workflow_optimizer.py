"""Workflow optimization strategies for improving execution performance.

This module provides functionality to analyze workflow execution history
and apply optimizations to improve performance, success rates, and resource utilization.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
from ..types import Task, WorkflowStep

logger = logging.getLogger(__name__)


class WorkflowOptimizationStrategy:
    """Base class for workflow optimization strategies.
    
    All optimization strategies should inherit from this class and implement
    the optimize method.
    """
    
    def __init__(self, name: str):
        """Initialize the optimization strategy.
        
        Args:
            name: Name of the strategy
        """
        self.name = name
        self.description = "Base workflow optimization strategy"
    
    async def optimize(
        self, 
        workflow: List[WorkflowStep], 
        execution_history: List[Dict[str, Any]]
    ) -> Tuple[List[WorkflowStep], Dict[str, Any]]:
        """Optimize a workflow based on execution history.
        
        Args:
            workflow: List of workflow steps to optimize
            execution_history: List of execution records
            
        Returns:
            Tuple of optimized workflow steps and optimization info
        """
        # Base implementation does nothing
        return workflow, {"strategy": self.name, "changes": []}


class ParallelizationOptimizer(WorkflowOptimizationStrategy):
    """Optimizes workflow by identifying steps that can be executed in parallel.
    
    This strategy analyzes dependencies between steps and marks independent
    steps as parallelizable to improve execution time.
    """
    
    def __init__(self):
        """Initialize the parallelization optimizer."""
        super().__init__("parallelization")
        self.description = "Identifies steps that can be executed in parallel"
    
    async def optimize(
        self, 
        workflow: List[WorkflowStep], 
        execution_history: List[Dict[str, Any]]
    ) -> Tuple[List[WorkflowStep], Dict[str, Any]]:
        """Optimize workflow parallelization.
        
        Args:
            workflow: List of workflow steps to optimize
            execution_history: List of execution records
            
        Returns:
            Tuple of optimized workflow steps and parallelization info
        """
        if not workflow:
            return workflow, {"strategy": self.name, "changes": []}
            
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(workflow)
        
        # Identify parallelizable steps
        parallelizable_steps = self._identify_parallelizable_steps(workflow, dependency_graph)
        
        # Apply parallelization
        optimized_workflow, changes = self._apply_parallelization(workflow, parallelizable_steps)
        
        return optimized_workflow, {
            "strategy": self.name,
            "changes": changes,
            "parallelizable_steps": len(parallelizable_steps),
            "total_steps": len(workflow),
            "parallelization_ratio": len(parallelizable_steps) / len(workflow) if workflow else 0
        }
    
    def _build_dependency_graph(self, workflow: List[WorkflowStep]) -> Dict[str, Set[str]]:
        """Build a dependency graph for the workflow.
        
        Args:
            workflow: List of workflow steps
            
        Returns:
            Dictionary mapping step names to sets of dependent step names
        """
        # Map of step_name -> steps that depend on it
        graph: Dict[str, Set[str]] = {}
        
        # Initialize graph
        for step in workflow:
            graph[step.task.name] = set()
        
        # Populate dependencies
        for step in workflow:
            for dep in step.dependencies:
                if dep in graph:
                    graph[dep].add(step.task.name)
        
        return graph
    
    def _identify_parallelizable_steps(
        self, workflow: List[WorkflowStep], dependency_graph: Dict[str, Set[str]]
    ) -> Set[str]:
        """Identify steps that can be executed in parallel.
        
        Args:
            workflow: List of workflow steps
            dependency_graph: Dependency graph from _build_dependency_graph
            
        Returns:
            Set of step names that can be executed in parallel
        """
        parallelizable = set()
        
        # Group steps by their dependency depth
        depth_map = self._calculate_dependency_depth(workflow)
        
        # Steps with the same depth that don't depend on each other can run in parallel
        depth_groups: Dict[int, List[str]] = {}
        for step_name, depth in depth_map.items():
            if depth not in depth_groups:
                depth_groups[depth] = []
            depth_groups[depth].append(step_name)
        
        # For each depth level, check which steps can run in parallel
        for depth, steps in depth_groups.items():
            if len(steps) <= 1:
                continue
                
            # Check each pair of steps at this depth
            for i, step1 in enumerate(steps):
                can_parallelize = True
                
                # A step can be parallelized if it doesn't have a conflict
                # with any other step at the same depth
                for step2 in steps[i+1:]:
                    if self._has_dependency_conflict(step1, step2, dependency_graph):
                        can_parallelize = False
                        break
                
                if can_parallelize:
                    parallelizable.add(step1)
        
        return parallelizable
    
    def _calculate_dependency_depth(self, workflow: List[WorkflowStep]) -> Dict[str, int]:
        """Calculate the dependency depth for each step.
        
        Args:
            workflow: List of workflow steps
            
        Returns:
            Dictionary mapping step names to their dependency depths
        """
        depths: Dict[str, int] = {}
        
        def get_depth(step_name: str) -> int:
            """Recursively calculate depth for a step."""
            if step_name in depths:
                return depths[step_name]
                
            # Find the step
            step = next((s for s in workflow if s.task.name == step_name), None)
            if not step:
                return 0
                
            # Depth is max depth of dependencies + 1
            if not step.dependencies:
                depths[step_name] = 0
                return 0
            
            max_dep_depth = max(get_depth(dep) for dep in step.dependencies)
            depths[step_name] = max_dep_depth + 1
            return depths[step_name]
        
        # Calculate depth for all steps
        for step in workflow:
            get_depth(step.task.name)
            
        return depths
    
    def _has_dependency_conflict(
        self, step1: str, step2: str, dependency_graph: Dict[str, Set[str]]
    ) -> bool:
        """Check if two steps have a dependency conflict.
        
        Args:
            step1: First step name
            step2: Second step name
            dependency_graph: Dependency graph
            
        Returns:
            True if steps have a conflict, False otherwise
        """
        # Direct conflict: one step depends on the other
        if step1 in dependency_graph and step2 in dependency_graph[step1]:
            return True
        if step2 in dependency_graph and step1 in dependency_graph[step2]:
            return True
            
        # Indirect conflict: they share a common dependent step
        for dep1 in dependency_graph.get(step1, set()):
            for dep2 in dependency_graph.get(step2, set()):
                if dep1 == dep2:
                    return True
        
        return False
    
    def _apply_parallelization(
        self, workflow: List[WorkflowStep], parallelizable_steps: Set[str]
    ) -> Tuple[List[WorkflowStep], List[Dict[str, Any]]]:
        """Apply parallelization to the workflow.
        
        Args:
            workflow: List of workflow steps
            parallelizable_steps: Set of step names that can be executed in parallel
            
        Returns:
            Tuple of optimized workflow steps and changes made
        """
        optimized_workflow = []
        changes = []
        
        for step in workflow:
            step_name = step.task.name
            
            if step_name in parallelizable_steps and not step.parallel:
                # Create a new step with parallel=True
                new_step = WorkflowStep(
                    task=step.task,
                    dependencies=step.dependencies,
                    parallel=True,
                    condition=step.condition
                )
                optimized_workflow.append(new_step)
                
                changes.append({
                    "type": "parallelize",
                    "step": step_name,
                    "before": False,
                    "after": True
                })
            else:
                optimized_workflow.append(step)
        
        return optimized_workflow, changes


class AgentSelectionOptimizer(WorkflowOptimizationStrategy):
    """Optimizes workflow by selecting the most effective agent for each task.
    
    This strategy analyzes past executions to determine which agents 
    performed best for similar tasks and assigns them.
    """
    
    def __init__(self):
        """Initialize the agent selection optimizer."""
        super().__init__("agent_selection")
        self.description = "Selects the most effective agent for each task"
    
    async def optimize(
        self, 
        workflow: List[WorkflowStep], 
        execution_history: List[Dict[str, Any]]
    ) -> Tuple[List[WorkflowStep], Dict[str, Any]]:
        """Optimize agent selection for workflow tasks.
        
        Args:
            workflow: List of workflow steps to optimize
            execution_history: List of execution records
            
        Returns:
            Tuple of optimized workflow steps and optimization info
        """
        if not workflow or not execution_history:
            return workflow, {"strategy": self.name, "changes": []}
        
        # Analyze execution history for agent performance
        agent_performance = self._analyze_agent_performance(execution_history)
        
        # Apply agent selection optimizations
        optimized_workflow, changes = self._apply_agent_optimization(workflow, agent_performance)
        
        return optimized_workflow, {
            "strategy": self.name,
            "changes": changes,
            "agents_analyzed": len(agent_performance)
        }
    
    def _analyze_agent_performance(
        self, execution_history: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        """Analyze agent performance from execution history.
        
        Args:
            execution_history: List of execution records
            
        Returns:
            Dictionary mapping task names to agent performance metrics
        """
        # Structure: task_name -> agent_type -> metrics
        performance: Dict[str, Dict[str, Dict[str, float]]] = {}
        
        for execution in execution_history:
            step_results = execution.get("step_results", {})
            
            for step_name, result in step_results.items():
                # Skip steps without metrics
                if "metrics" not in result:
                    continue
                    
                metrics = result["metrics"]
                # Skip entries without agent info
                if "agent_type" not in metrics:
                    continue
                    
                agent_type = metrics["agent_type"]
                success = result.get("status") == "success"
                execution_time = metrics.get("execution_time", 0.0)
                
                # Initialize performance tracking for this task
                if step_name not in performance:
                    performance[step_name] = {}
                
                # Initialize agent metrics for this task
                if agent_type not in performance[step_name]:
                    performance[step_name][agent_type] = {
                        "success_rate": 0.0,
                        "avg_execution_time": 0.0,
                        "execution_count": 0
                    }
                
                # Update metrics
                agent_metrics = performance[step_name][agent_type]
                count = agent_metrics["execution_count"]
                success_rate = agent_metrics["success_rate"]
                avg_time = agent_metrics["avg_execution_time"]
                
                # Compute new metrics
                new_count = count + 1
                new_success_rate = ((success_rate * count) + (1.0 if success else 0.0)) / new_count
                new_avg_time = ((avg_time * count) + execution_time) / new_count
                
                # Update performance record
                performance[step_name][agent_type] = {
                    "success_rate": new_success_rate,
                    "avg_execution_time": new_avg_time,
                    "execution_count": new_count
                }
        
        return performance
    
    def _apply_agent_optimization(
        self, 
        workflow: List[WorkflowStep], 
        agent_performance: Dict[str, Dict[str, Dict[str, float]]]
    ) -> Tuple[List[WorkflowStep], List[Dict[str, Any]]]:
        """Apply agent optimization to workflow steps.
        
        Args:
            workflow: List of workflow steps
            agent_performance: Agent performance metrics from _analyze_agent_performance
            
        Returns:
            Tuple of optimized workflow steps and changes made
        """
        optimized_workflow = []
        changes = []
        
        for step in workflow:
            step_name = step.task.name
            current_agent_type = step.task.agent_type
            
            # If we have performance data for this step
            if step_name in agent_performance:
                # Find the best performing agent
                best_agent = self._find_best_agent(agent_performance[step_name])
                
                if best_agent and best_agent != current_agent_type:
                    # Create a new task with the optimized agent type
                    new_task = Task(
                        id=step.task.id,
                        name=step.task.name,
                        description=step.task.description,
                        agent_type=best_agent,
                        parameters=step.task.parameters,
                        status=step.task.status,
                        max_retries=step.task.max_retries,
                        timeout=step.task.timeout,
                        created_at=step.task.created_at,
                        updated_at=step.task.updated_at,
                        output=step.task.output,
                        error=step.task.error,
                        retry_count=step.task.retry_count
                    )
                    
                    # Create a new step with the optimized task
                    new_step = WorkflowStep(
                        task=new_task,
                        dependencies=step.dependencies,
                        parallel=step.parallel,
                        condition=step.condition
                    )
                    
                    optimized_workflow.append(new_step)
                    
                    changes.append({
                        "type": "agent_selection",
                        "step": step_name,
                        "before": current_agent_type,
                        "after": best_agent,
                        "reason": "Historical performance analysis"
                    })
                else:
                    optimized_workflow.append(step)
            else:
                optimized_workflow.append(step)
        
        return optimized_workflow, changes
    
    def _find_best_agent(
        self, agent_metrics: Dict[str, Dict[str, float]]
    ) -> Optional[str]:
        """Find the best performing agent for a task.
        
        Args:
            agent_metrics: Dictionary mapping agent types to performance metrics
            
        Returns:
            Best agent type, or None if no clear best agent
        """
        if not agent_metrics:
            return None
            
        best_agent = None
        best_score = -1.0
        
        for agent_type, metrics in agent_metrics.items():
            # Skip agents with very few executions (insufficient data)
            if metrics["execution_count"] < 3:
                continue
                
            # Calculate an overall performance score
            # Weight success rate higher than execution time
            success_weight = 0.7
            time_weight = 0.3
            
            # Normalize execution time (lower is better)
            time_factor = 1.0 / (1.0 + metrics["avg_execution_time"])
            
            score = (metrics["success_rate"] * success_weight) + (time_factor * time_weight)
            
            if score > best_score:
                best_score = score
                best_agent = agent_type
        
        return best_agent


class ResourceOptimizer(WorkflowOptimizationStrategy):
    """Optimizes workflow to reduce resource consumption.
    
    This strategy analyzes resource usage patterns and optimizes 
    steps to minimize resource consumption while maintaining performance.
    """
    
    def __init__(self):
        """Initialize the resource optimizer."""
        super().__init__("resource_optimization")
        self.description = "Optimizes resource usage in workflows"
    
    async def optimize(
        self, 
        workflow: List[WorkflowStep], 
        execution_history: List[Dict[str, Any]]
    ) -> Tuple[List[WorkflowStep], Dict[str, Any]]:
        """Optimize resource usage in the workflow.
        
        Args:
            workflow: List of workflow steps to optimize
            execution_history: List of execution records
            
        Returns:
            Tuple of optimized workflow steps and optimization info
        """
        if not workflow or not execution_history:
            return workflow, {"strategy": self.name, "changes": []}
        
        # Analyze resource usage patterns
        resource_patterns = self._analyze_resource_usage(execution_history)
        
        # Apply resource optimizations
        optimized_workflow, changes = self._apply_resource_optimizations(workflow, resource_patterns)
        
        return optimized_workflow, {
            "strategy": self.name,
            "changes": changes,
            "resource_types_analyzed": len(resource_patterns)
        }
    
    def _analyze_resource_usage(
        self, execution_history: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """Analyze resource usage patterns from execution history.
        
        Args:
            execution_history: List of execution records
            
        Returns:
            Dictionary mapping step names to resource usage metrics
        """
        resource_usage: Dict[str, Dict[str, float]] = {}
        
        for execution in execution_history:
            step_results = execution.get("step_results", {})
            
            for step_name, result in step_results.items():
                # Skip steps without metrics
                if "metrics" not in result:
                    continue
                    
                metrics = result["metrics"]
                # Skip entries without resource usage
                if "resource_usage" not in metrics:
                    continue
                    
                # Initialize resource tracking for this step
                if step_name not in resource_usage:
                    resource_usage[step_name] = {}
                
                # Update resource usage metrics
                for resource_type, usage in metrics["resource_usage"].items():
                    if resource_type not in resource_usage[step_name]:
                        resource_usage[step_name][resource_type] = 0.0
                        
                    # Keep track of average usage
                    current = resource_usage[step_name][resource_type]
                    count = resource_usage.get("_count", 0) + 1
                    resource_usage[step_name][resource_type] = ((current * (count - 1)) + usage) / count
                    resource_usage[step_name]["_count"] = count
        
        return resource_usage
    
    def _apply_resource_optimizations(
        self, 
        workflow: List[WorkflowStep], 
        resource_patterns: Dict[str, Dict[str, float]]
    ) -> Tuple[List[WorkflowStep], List[Dict[str, Any]]]:
        """Apply resource optimizations to workflow steps.
        
        Args:
            workflow: List of workflow steps
            resource_patterns: Resource usage metrics from _analyze_resource_usage
            
        Returns:
            Tuple of optimized workflow steps and changes made
        """
        optimized_workflow = []
        changes = []
        
        for step in workflow:
            step_name = step.task.name
            
            # If we have resource data for this step
            if step_name in resource_patterns:
                # Check for potential optimizations
                optimizations = self._identify_resource_optimizations(step, resource_patterns[step_name])
                
                if optimizations:
                    # Create a new task with optimized parameters
                    new_params = dict(step.task.parameters)
                    
                    # Apply each optimization
                    for opt in optimizations:
                        param = opt["parameter"]
                        new_value = opt["new_value"]
                        
                        if param in new_params:
                            new_params[param] = new_value
                    
                    new_task = Task(
                        id=step.task.id,
                        name=step.task.name,
                        description=step.task.description,
                        agent_type=step.task.agent_type,
                        parameters=new_params,
                        status=step.task.status,
                        max_retries=step.task.max_retries,
                        timeout=step.task.timeout,
                        created_at=step.task.created_at,
                        updated_at=step.task.updated_at,
                        output=step.task.output,
                        error=step.task.error,
                        retry_count=step.task.retry_count
                    )
                    
                    # Create a new step with the optimized task
                    new_step = WorkflowStep(
                        task=new_task,
                        dependencies=step.dependencies,
                        parallel=step.parallel,
                        condition=step.condition
                    )
                    
                    optimized_workflow.append(new_step)
                    
                    for opt in optimizations:
                        changes.append({
                            "type": "resource_optimization",
                            "step": step_name,
                            "parameter": opt["parameter"],
                            "before": opt["old_value"],
                            "after": opt["new_value"],
                            "reason": opt["reason"]
                        })
                else:
                    optimized_workflow.append(step)
            else:
                optimized_workflow.append(step)
        
        return optimized_workflow, changes
    
    def _identify_resource_optimizations(
        self, step: WorkflowStep, resource_metrics: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Identify potential resource optimizations for a step.
        
        Args:
            step: Workflow step to optimize
            resource_metrics: Resource usage metrics for this step
            
        Returns:
            List of optimization suggestions
        """
        optimizations = []
        
        # Check common parameters that affect resource usage
        params = step.task.parameters
        
        # Examples of resource optimization rules
        # (These would be expanded based on specific agent capabilities)
        
        # Optimize batch size parameters
        if "batch_size" in params:
            current_batch_size = params["batch_size"]
            if isinstance(current_batch_size, int) and current_batch_size > 1:
                # If memory usage is high but CPU is low, reduce batch size
                if resource_metrics.get("memory", 0) > 1000 and resource_metrics.get("cpu", 0) < 50:
                    optimized_size = max(1, current_batch_size // 2)
                    optimizations.append({
                        "parameter": "batch_size",
                        "old_value": current_batch_size,
                        "new_value": optimized_size,
                        "reason": "High memory usage with low CPU utilization"
                    })
        
        # Optimize timeout parameters
        if "timeout" in params and resource_metrics.get("_count", 0) >= 5:
            current_timeout = params["timeout"]
            avg_execution_time = resource_metrics.get("execution_time", 0)
            
            # If actual execution time is consistently much lower than timeout
            if avg_execution_time > 0 and current_timeout > 3 * avg_execution_time:
                # Reduce timeout to save resources
                optimized_timeout = max(avg_execution_time * 2, 1)  # Provide some buffer
                optimizations.append({
                    "parameter": "timeout",
                    "old_value": current_timeout,
                    "new_value": optimized_timeout,
                    "reason": "Excessive timeout relative to average execution time"
                })
        
        # Add more optimization rules as needed
        
        return optimizations


class WorkflowOptimizer:
    """Applies optimization strategies to improve workflow performance.
    
    This class manages a set of optimization strategies and applies them
    to workflows based on execution history and performance goals.
    
    Attributes:
        strategies: List of optimization strategies
    """
    
    def __init__(self):
        """Initialize the workflow optimizer."""
        self.strategies: List[WorkflowOptimizationStrategy] = [
            ParallelizationOptimizer(),
            AgentSelectionOptimizer(),
            ResourceOptimizer(),
        ]
    
    async def optimize_workflow(
        self, 
        workflow_id: str,
        workflow: List[WorkflowStep], 
        execution_history: List[Dict[str, Any]],
        target_metrics: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[WorkflowStep], Dict[str, Any]]:
        """Optimize a workflow based on execution history.
        
        Args:
            workflow_id: ID of the workflow to optimize
            workflow: List of workflow steps to optimize
            execution_history: List of execution records
            target_metrics: Optional metrics to target in optimization
            
        Returns:
            Tuple of optimized workflow steps and detailed optimization results
        """
        if not workflow:
            return workflow, {"workflow_id": workflow_id, "optimizations": []}
            
        logger.info(f"Optimizing workflow {workflow_id} with {len(self.strategies)} strategies")
        
        # Track original workflow for comparison
        original_workflow = workflow
        
        # Apply each optimization strategy in sequence
        optimization_results = []
        
        for strategy in self.strategies:
            try:
                logger.info(f"Applying optimization strategy: {strategy.name}")
                optimized_workflow, strategy_results = await strategy.optimize(workflow, execution_history)
                
                # Only update workflow if changes were made
                if strategy_results.get("changes"):
                    workflow = optimized_workflow
                    optimization_results.append(strategy_results)
                    logger.info(f"Strategy {strategy.name} applied {len(strategy_results.get('changes', []))} changes")
                else:
                    logger.info(f"Strategy {strategy.name} made no changes")
                
            except Exception as e:
                logger.error(f"Error applying optimization strategy {strategy.name}: {str(e)}")
        
        # Generate summary of all optimizations
        optimization_summary = self._generate_optimization_summary(
            workflow_id, original_workflow, workflow, optimization_results
        )
        
        return workflow, optimization_summary
    
    def _generate_optimization_summary(
        self, 
        workflow_id: str,
        original_workflow: List[WorkflowStep],
        optimized_workflow: List[WorkflowStep],
        optimization_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a summary of all optimizations applied.
        
        Args:
            workflow_id: ID of the optimized workflow
            original_workflow: Original workflow steps
            optimized_workflow: Optimized workflow steps
            optimization_results: Results from each optimization strategy
            
        Returns:
            Dictionary containing optimization summary
        """
        # Count the number of steps modified
        modified_steps = set()
        for result in optimization_results:
            for change in result.get("changes", []):
                modified_steps.add(change.get("step"))
        
        # Compare parallelization
        original_parallel = sum(1 for step in original_workflow if step.parallel)
        optimized_parallel = sum(1 for step in optimized_workflow if step.parallel)
        
        return {
            "workflow_id": workflow_id,
            "timestamp": datetime.utcnow().isoformat(),
            "strategies_applied": len(optimization_results),
            "total_changes": sum(len(result.get("changes", [])) for result in optimization_results),
            "steps_modified": len(modified_steps),
            "total_steps": len(original_workflow),
            "modification_ratio": len(modified_steps) / len(original_workflow) if original_workflow else 0,
            "parallelization_improvement": (optimized_parallel - original_parallel) / len(original_workflow) if original_workflow else 0,
            "optimizations": optimization_results
        }
    
    def add_strategy(self, strategy: WorkflowOptimizationStrategy) -> None:
        """Add a new optimization strategy.
        
        Args:
            strategy: Optimization strategy to add
        """
        self.strategies.append(strategy)
        logger.info(f"Added optimization strategy: {strategy.name}")
    
    def remove_strategy(self, strategy_name: str) -> bool:
        """Remove an optimization strategy by name.
        
        Args:
            strategy_name: Name of the strategy to remove
            
        Returns:
            True if strategy was removed, False otherwise
        """
        for i, strategy in enumerate(self.strategies):
            if strategy.name == strategy_name:
                self.strategies.pop(i)
                logger.info(f"Removed optimization strategy: {strategy_name}")
                return True
        
        logger.warning(f"Optimization strategy not found: {strategy_name}")
        return False 