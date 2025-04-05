"""Orchestrator implementation for managing workflow execution."""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from .agents import BaseAgent
from .config import AgentConfig
from .ledgers import TaskLedger, ProgressLedger
from .types import Task, WorkflowStep

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Agent responsible for orchestrating workflow execution.
    
    Attributes:
        config: Configuration for the orchestrator
        task_ledger: Ledger for tracking tasks
        progress_ledger: Ledger for tracking workflow progress
        agents: Dictionary of registered agents
    """

    def __init__(
        self,
        config: AgentConfig,
        task_ledger: TaskLedger,
        progress_ledger: ProgressLedger
    ):
        """Initialize the orchestrator.
        
        Args:
            config: Configuration for the orchestrator
            task_ledger: Task tracking ledger
            progress_ledger: Progress tracking ledger
        """
        self.config = config
        self.task_ledger = task_ledger
        self.progress_ledger = progress_ledger
        self.agents: Dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent):
        """Register an agent with the orchestrator.
        
        Args:
            agent: Agent instance to register
        """
        self.agents[agent.type] = agent

    async def execute_workflow(self, workflow: List[WorkflowStep]) -> Dict[str, Any]:
        """Execute a workflow.
        
        Args:
            workflow: List of workflow steps to execute
            
        Returns:
            Dictionary containing workflow execution results
        """
        workflow_id = f"workflow_{datetime.now().timestamp()}"
        await self.progress_ledger.register_workflow(workflow_id, workflow)
        
        completed_steps = []
        failed_steps = []
        retried_steps = []
        metrics = {
            "execution_time": 0.0,
            "resource_usage": {},
            "success_rate": 0.0
        }
        
        start_time = datetime.now()
        
        try:
            while len(completed_steps) + len(failed_steps) < len(workflow):
                ready_steps = self.progress_ledger.get_ready_steps(workflow_id)
                if not ready_steps:
                    # Check for deadlock
                    remaining = set(step.task.name for step in workflow) - set(completed_steps) - set(failed_steps)
                    if remaining and not ready_steps:
                        raise RuntimeError(f"Deadlock detected. Remaining steps: {remaining}")
                    await asyncio.sleep(0.1)
                    continue

                # Execute ready steps in parallel
                tasks = []
                for step_name in ready_steps:
                    step = next(s for s in workflow if s.task.name == step_name)
                    tasks.append(self._execute_step(workflow_id, step))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for step_name, result in zip(ready_steps, results):
                    if isinstance(result, Exception):
                        logger.error(f"Step {step_name} failed: {str(result)}")
                        failed_steps.append(step_name)
                        await self.progress_ledger.update_step_status(workflow_id, step_name, "failed")
                    else:
                        if result.get("retried", False):
                            retried_steps.append(step_name)
                        completed_steps.append(step_name)
                        await self.progress_ledger.update_step_status(workflow_id, step_name, "completed")
                        
                        # Update metrics
                        step_metrics = result.get("metrics", {})
                        for key, value in step_metrics.items():
                            if key not in metrics["resource_usage"]:
                                metrics["resource_usage"][key] = 0
                            metrics["resource_usage"][key] += value

        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "metrics": metrics
            }

        # Calculate final metrics
        end_time = datetime.now()
        metrics["execution_time"] = (end_time - start_time).total_seconds()
        metrics["success_rate"] = len(completed_steps) / len(workflow)

        return {
            "status": "success" if not failed_steps else "partial_success",
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "retried_steps": retried_steps,
            "metrics": metrics
        }

    async def _execute_step(self, workflow_id: str, step: WorkflowStep) -> Dict[str, Any]:
        """Execute a single workflow step.
        
        Args:
            workflow_id: ID of the workflow
            step: Step to execute
            
        Returns:
            Dictionary containing step execution results
        """
        task = step.task
        agent = self.agents.get(task.agent_type)
        
        if not agent:
            raise ValueError(f"No agent found for type: {task.agent_type}")
        
        if not await agent.validate_task(task):
            raise ValueError(f"Task {task.name} is not valid for agent {task.agent_type}")
        
        # Add task to ledger
        task_id = await self.task_ledger.add_task(task)
        
        # Execute with retry logic
        retries = 0
        while retries <= task.max_retries:
            try:
                # Preprocess task
                processed_task = await agent.preprocess_task(task)
                
                # Execute task
                result = await agent.execute(processed_task)
                
                # Postprocess result
                final_result = await agent.postprocess_result(result)
                
                # Update task result
                await self.task_ledger.update_task_result(task_id, final_result)
                
                return {
                    "status": "success",
                    "result": final_result,
                    "retried": retries > 0,
                    "metrics": result.get("metrics", {})
                }
                
            except Exception as e:
                retries += 1
                if retries > task.max_retries:
                    raise
                logger.warning(f"Retrying task {task.name} after error: {str(e)}")
                await asyncio.sleep(1 * retries)  # Exponential backoff
        
        raise RuntimeError(f"Task {task.name} failed after {task.max_retries} retries") 