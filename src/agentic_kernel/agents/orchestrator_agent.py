"""Orchestrator Agent for managing multi-agent workflows."""

from typing import Dict, List, Optional, Any
import asyncio
import logging
import time
from datetime import datetime
import psutil

from .base import Agent
from ..ledgers import TaskLedger, ProgressLedger, PlanStep, ProgressEntry


class OrchestratorAgent(Agent):
    """Agent responsible for orchestrating multi-agent workflows."""
    
    def __init__(self, name: str, description: str, llm: Any, config: Dict[str, Any] = None):
        """Initialize the orchestrator agent."""
        super().__init__(name, description, config)
        self.llm = llm
        self.available_agents: Dict[str, Agent] = {}
        
        # Default configuration
        self.config = config or {
            "max_planning_attempts": 3,
            "reflection_threshold": 0.7,
            "max_task_retries": 2
        }

    def register_agent(self, agent: Agent) -> None:
        """Register an agent with the orchestrator."""
        self.available_agents[agent.__class__.__name__] = agent
        
    async def execute_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a task by creating and managing a workflow."""
        task_ledger = TaskLedger(
            goal=task_description,
            initial_facts=context.get("facts", []) if context else [],
            assumptions=context.get("assumptions", []) if context else []
        )
        
        progress_ledger = ProgressLedger(
            task_id=context.get("task_id", "default_task") if context else "default_task",
            current_status="not_started"
        )
        
        try:
            result = await self.execute_workflow(task_ledger, progress_ledger)
            return {
                "status": result["status"],
                "output": result.get("output", ""),
                "error": result.get("error", None),
                "metrics": result.get("metrics", {})
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "output": "",
                "metrics": {}
            }
        
    async def execute_workflow(
        self,
        task_ledger: TaskLedger,
        progress_ledger: ProgressLedger,
        allow_parallel: bool = False
    ) -> Dict[str, Any]:
        """Execute a workflow based on the task ledger and progress ledger."""
        progress_ledger.current_status = "in_progress"
        completed_steps = []
        retry_count = 0
        replanning_events = []
        parallel_executions = 0
        metrics = {}
        success_rate = 1.0
        
        try:
            while True:
                # Get executable steps
                executable_steps = self._get_executable_steps(task_ledger.plan, completed_steps)
                if not executable_steps:
                    if not task_ledger.plan:  # No steps at all
                        break
                    if all(step.status == "completed" for step in task_ledger.plan):
                        break  # All steps completed
                    # If we have steps but none are executable, evaluate progress
                    try:
                        progress = await self._evaluate_progress(task_ledger, completed_steps)
                        success_rate = progress.get("success_rate", 1.0)
                        if progress["needs_replanning"]:
                            # Attempt replanning
                            new_plan = await self._replan_workflow(task_ledger, progress["suggestions"])
                            if new_plan:
                                task_ledger.plan = new_plan
                                replanning_events.append({
                                    "timestamp": datetime.now().isoformat(),
                                    "reason": "Progress evaluation"
                                })
                                continue  # Try again with new plan
                    except Exception as e:
                        return {
                            "status": "error",
                            "error": str(e),
                            "completed_steps": completed_steps,
                            "retry_count": retry_count,
                            "replanning_events": replanning_events,
                            "parallel_executions": parallel_executions,
                            "metrics": metrics,
                            "success_rate": success_rate
                        }
                    # If we can't replan, we're stuck
                    return {
                        "status": "error",
                        "error": "No executable steps available and replanning failed",
                        "completed_steps": completed_steps,
                        "retry_count": retry_count,
                        "replanning_events": replanning_events,
                        "parallel_executions": parallel_executions,
                        "metrics": metrics,
                        "success_rate": success_rate
                    }
                
                # Execute steps (parallel if allowed)
                if allow_parallel and len(executable_steps) > 1:
                    tasks = [self._execute_step(step) for step in executable_steps]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    parallel_executions += 1
                else:
                    results = []
                    for step in executable_steps:
                        result = await self._execute_step(step)
                        results.append(result)
                
                # Process results
                for step, result in zip(executable_steps, results):
                    if isinstance(result, Exception) or (isinstance(result, dict) and result.get("status") == "error"):
                        # Handle step failure
                        error_msg = str(result) if isinstance(result, Exception) else result.get("error", "Unknown error")
                        retry_result = await self._handle_step_failure(step, error_msg, retry_count)
                        if retry_result["status"] == "error":
                            return {
                                "status": "error",
                                "error": error_msg,
                                "completed_steps": completed_steps,
                                "retry_count": retry_count,
                                "replanning_events": replanning_events,
                                "parallel_executions": parallel_executions,
                                "metrics": metrics,
                                "success_rate": success_rate
                            }
                        retry_count = retry_result["retry_count"]
                        if retry_result.get("replanned"):
                            replanning_events.append({
                                "step": step.step_id,
                                "timestamp": datetime.now().isoformat()
                            })
                        if retry_result["status"] == "retry":
                            step.status = "pending"  # Reset status for retry
                            continue
                    else:
                        step.status = "completed"
                        completed_steps.append(step.step_id)
                        # Collect metrics from successful execution
                        if isinstance(result, dict) and "metrics" in result:
                            metrics = {**metrics, **result["metrics"]}
                
                try:
                    # Evaluate progress
                    progress = await self._evaluate_progress(task_ledger, completed_steps)
                    success_rate = progress.get("success_rate", 1.0)
                    if progress["needs_replanning"]:
                        # Attempt replanning
                        new_plan = await self._replan_workflow(task_ledger, progress["suggestions"])
                        if new_plan:
                            task_ledger.plan = new_plan
                            replanning_events.append({
                                "timestamp": datetime.now().isoformat(),
                                "reason": "Progress evaluation"
                            })
                        else:
                            return {
                                "status": "error",
                                "error": "Failed to replan workflow",
                                "completed_steps": completed_steps,
                                "retry_count": retry_count,
                                "replanning_events": replanning_events,
                                "parallel_executions": parallel_executions,
                                "metrics": metrics,
                                "success_rate": success_rate
                            }
                except Exception as e:
                    return {
                        "status": "error",
                        "error": str(e),
                        "completed_steps": completed_steps,
                        "retry_count": retry_count,
                        "replanning_events": replanning_events,
                        "parallel_executions": parallel_executions,
                        "metrics": metrics,
                        "success_rate": success_rate
                    }
            
            # All steps completed
            progress_ledger.current_status = "completed"
            return {
                "status": "success",
                "completed_steps": completed_steps,
                "retry_count": retry_count,
                "replanning_events": replanning_events,
                "parallel_executions": parallel_executions,
                "success_rate": success_rate,
                "metrics": metrics
            }
            
        except Exception as e:
            progress_ledger.current_status = "failed"
            return {
                "status": "error",
                "error": str(e),
                "completed_steps": completed_steps,
                "retry_count": retry_count,
                "replanning_events": replanning_events,
                "parallel_executions": parallel_executions,
                "metrics": metrics,
                "success_rate": success_rate
            }
    
    async def _execute_step(self, step: PlanStep) -> Dict[str, Any]:
        """Execute a single step in the workflow."""
        try:
            agent = await self._determine_agent_for_step(step)
            if not agent:
                return {
                    "status": "error",
                    "error": f"No suitable agent found for step {step.step_id}"
                }
            
            start_time = time.time()
            result = await agent.execute_task(step.description, step.context)
            duration = time.time() - start_time
            
            # Ensure result is a dictionary
            if not isinstance(result, dict):
                result = {"output": result}
            
            # Add execution metrics
            metrics = result.get("metrics", {})
            metrics.update({
                "duration": duration,
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024  # MB
            })
            
            result["metrics"] = metrics
            result["status"] = result.get("status", "success")
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _determine_agent_for_step(self, step: PlanStep) -> Optional[Agent]:
        """Determine which agent should handle a step based on its description."""
        # Simple keyword matching for now
        keywords = {
            "WebSurferAgent": ["research", "documentation", "web", "online"],
            "FileSurferAgent": ["file", "codebase", "analyze", "read"],
            "CoderAgent": ["implement", "code", "generate", "develop"],
            "TerminalAgent": ["execute", "run", "install", "build"]
        }
        
        max_matches = 0
        best_agent = None
        
        for agent_name, agent_keywords in keywords.items():
            matches = sum(1 for keyword in agent_keywords if keyword.lower() in step.description.lower())
            if matches > max_matches and agent_name in self.available_agents:
                max_matches = matches
                best_agent = self.available_agents[agent_name]
        
        return best_agent or next(iter(self.available_agents.values()))
    
    def _get_executable_steps(self, plan: List[PlanStep], completed_steps: List[str]) -> List[PlanStep]:
        """Get steps that can be executed based on their dependencies."""
        executable = []
        for step in plan:
            if step.status != "completed" and step.step_id not in completed_steps:
                if all(dep in completed_steps for dep in step.depends_on):
                    executable.append(step)
        return executable
    
    async def _handle_step_failure(
        self,
        step: PlanStep,
        error: str,
        current_retry_count: int
    ) -> Dict[str, Any]:
        """Handle a failed step execution."""
        if current_retry_count < self.config["max_task_retries"]:
            # Retry the step
            return {
                "status": "retry",
                "retry_count": current_retry_count + 1
            }
        
        # Attempt replanning
        new_plan = await self._replan_workflow(
            TaskLedger(
                goal=f"Alternative approach for: {step.description}",
                initial_facts=[f"Previous attempt failed: {error}"],
                assumptions=[]
            ),
            [f"Previous approach failed: {error}"]
        )
        
        if new_plan:
            return {
                "status": "success",
                "retry_count": current_retry_count,
                "replanned": True
            }
        
        return {
            "status": "error",
            "error": f"Step failed after {current_retry_count} retries and replanning attempt",
            "retry_count": current_retry_count
        }
    
    async def _evaluate_progress(
        self,
        task_ledger: TaskLedger,
        completed_steps: List[str]
    ) -> Dict[str, Any]:
        """Evaluate the current progress and determine if replanning is needed."""
        return await self.llm.evaluate_progress(task_ledger, completed_steps)
    
    async def _replan_workflow(
        self,
        task_ledger: TaskLedger,
        suggestions: List[str]
    ) -> Optional[List[PlanStep]]:
        """Replan the workflow based on the current state and suggestions."""
        try:
            return await self.llm.replan_task(task_ledger, suggestions)
        except Exception as e:
            print(f"Replanning failed: {str(e)}")
            return None 