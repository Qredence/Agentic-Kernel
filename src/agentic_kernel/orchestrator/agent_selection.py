"""Agent selection utilities for the orchestrator.

This module provides functionality to intelligently select agents based on task requirements.
It analyzes task requirements and capabilities of available agents to select the best match.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import asyncio

from ..agents.base import BaseAgent, TaskCapability
from ..types import Task

logger = logging.getLogger(__name__)


class AgentSkillMatrix:
    """Manages agent skill information and selection logic.
    
    This class maintains information about agent capabilities and provides
    methods to match tasks with appropriate agents based on capabilities,
    historical performance, and specialized knowledge.
    
    Attributes:
        agent_capabilities: Dictionary mapping agent_id to capabilities
        agent_performance: Dictionary tracking agent performance metrics
        agent_specialization: Dictionary mapping domain areas to preferred agents
    """
    
    def __init__(self):
        """Initialize the agent skill matrix."""
        self.agent_capabilities: Dict[str, Dict[str, TaskCapability]] = {}
        self.agent_performance: Dict[str, Dict[str, float]] = {}
        self.agent_specialization: Dict[str, List[str]] = {}
        
    async def register_agent_capabilities(self, agent: BaseAgent) -> None:
        """Register an agent's capabilities with the skill matrix.
        
        Args:
            agent: The agent to register
        """
        capabilities = agent.get_capabilities()
        self.agent_capabilities[agent.agent_id] = capabilities.get("supported_tasks", {})
        logger.info(f"Registered capabilities for agent {agent.type} ({agent.agent_id})")
        
        # Initialize performance tracking
        if agent.agent_id not in self.agent_performance:
            self.agent_performance[agent.agent_id] = {
                "success_rate": 1.0,  # Start optimistic
                "avg_execution_time": 0.0,
                "task_count": 0,
            }
        
    def register_agent_specialization(self, agent_id: str, domains: List[str]) -> None:
        """Register an agent's specialized domains.
        
        Args:
            agent_id: The agent ID
            domains: List of domain areas the agent specializes in
        """
        for domain in domains:
            if domain not in self.agent_specialization:
                self.agent_specialization[domain] = []
            self.agent_specialization[domain].append(agent_id)
        
    def update_agent_performance(
        self, agent_id: str, success: bool, execution_time: float
    ) -> None:
        """Update performance metrics for an agent.
        
        Args:
            agent_id: The agent ID
            success: Whether the task executed successfully
            execution_time: Time taken to execute the task
        """
        if agent_id not in self.agent_performance:
            logger.warning(f"Attempting to update performance for unknown agent: {agent_id}")
            return
            
        perf = self.agent_performance[agent_id]
        
        # Update metrics with exponential moving average
        task_count = perf["task_count"] + 1
        success_rate = perf["success_rate"]
        avg_time = perf["avg_execution_time"]
        
        # Weight recent performance more heavily
        alpha = min(0.3, 1.0 / task_count) if task_count > 0 else 0.3
        
        # Update success rate
        new_success_rate = success_rate * (1 - alpha) + (1.0 if success else 0.0) * alpha
        
        # Update average execution time
        new_avg_time = avg_time * (1 - alpha) + execution_time * alpha
        
        # Store updated metrics
        self.agent_performance[agent_id] = {
            "success_rate": new_success_rate,
            "avg_execution_time": new_avg_time,
            "task_count": task_count,
        }
        
    async def select_agent_for_task(
        self, task: Task, available_agents: Dict[str, BaseAgent]
    ) -> Tuple[Optional[str], float]:
        """Select the best agent for a given task.
        
        This method analyzes task requirements and agent capabilities to select
        the most appropriate agent for executing the task.
        
        Args:
            task: The task to be executed
            available_agents: Dictionary of available agents
            
        Returns:
            Tuple containing the selected agent ID and a confidence score
        """
        # Check if task specifies a required agent type
        if task.agent_type and task.agent_type != "any":
            # Find agents of the specified type
            matching_agents = [
                agent_id for agent_id, agent in available_agents.items()
                if agent.type == task.agent_type
            ]
            
            if not matching_agents:
                logger.warning(
                    f"No agents of required type '{task.agent_type}' available for task '{task.name}'"
                )
                return None, 0.0
                
            # If multiple agents match, select based on performance
            if len(matching_agents) > 1:
                return self._select_best_performing_agent(matching_agents), 1.0
            
            # Single matching agent
            return matching_agents[0], 1.0
            
        # No specific agent type required, select based on capabilities
        return await self._select_agent_by_capability(task, available_agents)
        
    async def _select_agent_by_capability(
        self, task: Task, available_agents: Dict[str, BaseAgent]
    ) -> Tuple[Optional[str], float]:
        """Select an agent based on task capabilities.
        
        Args:
            task: The task to be executed
            available_agents: Dictionary of available agents
            
        Returns:
            Tuple containing the selected agent ID and a confidence score
        """
        best_agent_id = None
        highest_score = 0.0
        
        # Extract task requirements
        task_name = task.name.lower()
        task_desc = task.description.lower() if task.description else ""
        task_params = set(task.parameters.keys())
        
        # Calculate capability scores for each agent
        capability_scores = {}
        
        # Gather capability information from each agent
        capability_check_tasks = []
        for agent_id, agent in available_agents.items():
            # Skip gathering if we already have the info
            if agent_id in self.agent_capabilities:
                continue
                
            # Queue capability check
            capability_check_tasks.append(self.register_agent_capabilities(agent))
            
        # Wait for all capability checks to complete
        if capability_check_tasks:
            await asyncio.gather(*capability_check_tasks)
            
        # Score each agent
        for agent_id, agent in available_agents.items():
            # Skip agents with no registered capabilities
            if agent_id not in self.agent_capabilities:
                continue
                
            agent_caps = self.agent_capabilities[agent_id]
            score = 0.0
            
            # Check each capability
            for cap_name, cap_info in agent_caps.items():
                cap_score = 0.0
                
                # Match by capability name
                if cap_name.lower() in task_name:
                    cap_score += 0.6
                    
                # Match by capability description
                cap_desc = cap_info.get("description", "").lower()
                if cap_desc and any(term in task_desc for term in cap_desc.split()):
                    cap_score += 0.3
                    
                # Match by parameters
                cap_params = set(cap_info.get("parameters", []))
                param_match_ratio = len(task_params.intersection(cap_params)) / max(len(task_params), 1)
                cap_score += param_match_ratio * 0.4
                
                # Apply specialization bonus
                for domain, specialists in self.agent_specialization.items():
                    if agent_id in specialists and domain.lower() in task_desc:
                        cap_score += 0.3
                        break
                        
                # Update overall score with highest capability match
                score = max(score, cap_score)
                
            # Apply performance adjustment
            if agent_id in self.agent_performance:
                perf = self.agent_performance[agent_id]
                # Weight performance more heavily for agents with more experience
                perf_weight = min(0.5, perf["task_count"] / 20)
                score = score * (1 - perf_weight) + perf["success_rate"] * perf_weight
                
            capability_scores[agent_id] = score
            
            # Update best agent if this one scores higher
            if score > highest_score:
                highest_score = score
                best_agent_id = agent_id
                
        # Return best agent with normalized confidence score
        confidence = highest_score / 2.0  # Normalize to 0-1 range
        return best_agent_id, min(confidence, 1.0)
        
    def _select_best_performing_agent(self, agent_ids: List[str]) -> str:
        """Select the best performing agent from a list of candidates.
        
        Args:
            agent_ids: List of candidate agent IDs
            
        Returns:
            ID of the best performing agent
        """
        best_agent = agent_ids[0]  # Default to first
        best_score = 0.0
        
        for agent_id in agent_ids:
            if agent_id in self.agent_performance:
                perf = self.agent_performance[agent_id]
                # Calculate performance score weighting success rate more than speed
                perf_score = (perf["success_rate"] * 0.8) + (1.0 / (1.0 + perf["avg_execution_time"])) * 0.2
                
                if perf_score > best_score:
                    best_score = perf_score
                    best_agent = agent_id
                    
        return best_agent
        
        
class AgentSelector:
    """Provides agent selection services for the orchestrator.
    
    This class handles the high-level agent selection process, including
    caching, fallback strategies, and context-aware selection.
    
    Attributes:
        skill_matrix: The agent skill matrix for capability-based selection
        selection_cache: Cache of recent task-to-agent mappings
        fallback_strategies: Ordered list of fallback strategies
    """
    
    def __init__(self):
        """Initialize the agent selector."""
        self.skill_matrix = AgentSkillMatrix()
        self.selection_cache: Dict[str, str] = {}  # task_type -> agent_id
        self.min_confidence_threshold = 0.4
        
    async def select_agent(
        self, task: Task, available_agents: Dict[str, BaseAgent],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Select the best agent for executing a task.
        
        Args:
            task: The task to be executed
            available_agents: Dictionary of available agents
            context: Optional execution context
            
        Returns:
            ID of the selected agent, or None if no suitable agent found
        """
        # Early exit if no agents available
        if not available_agents:
            logger.warning("No agents available for selection")
            return None
            
        # Check cache for frequently used task types
        task_type = task.name.split('_')[0] if '_' in task.name else task.name
        if task_type in self.selection_cache:
            cached_agent_id = self.selection_cache[task_type]
            if cached_agent_id in available_agents:
                logger.debug(f"Using cached agent selection for task type: {task_type}")
                return cached_agent_id
                
        # Try capability-based selection
        agent_id, confidence = await self.skill_matrix.select_agent_for_task(
            task, available_agents
        )
        
        # If confidence is high enough, cache the result
        if agent_id and confidence >= self.min_confidence_threshold:
            self.selection_cache[task_type] = agent_id
            logger.debug(
                f"Selected agent {agent_id} for task '{task.name}' with confidence {confidence:.2f}"
            )
            return agent_id
            
        # Fallback if no suitable agent found or confidence too low
        if not agent_id or confidence < 0.2:  # Very low confidence
            fallback_id = self._fallback_selection(task, available_agents, context)
            logger.debug(
                f"Using fallback selection for task '{task.name}': {fallback_id}"
            )
            return fallback_id
            
        # Use selected agent even with medium confidence
        return agent_id
        
    def _fallback_selection(
        self, task: Task, available_agents: Dict[str, BaseAgent],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Select an agent using fallback strategies.
        
        Args:
            task: The task to be executed
            available_agents: Dictionary of available agents
            context: Optional execution context
            
        Returns:
            ID of the selected agent, or None if no suitable agent found
        """
        # Strategy 1: Try to find a generalist agent
        for agent_id, agent in available_agents.items():
            if agent.type in ["generalist", "assistant"]:
                return agent_id
                
        # Strategy 2: Select agent with highest success rate
        best_agent_id = None
        best_success_rate = 0.0
        
        for agent_id in available_agents:
            if agent_id in self.skill_matrix.agent_performance:
                success_rate = self.skill_matrix.agent_performance[agent_id]["success_rate"]
                if success_rate > best_success_rate:
                    best_success_rate = success_rate
                    best_agent_id = agent_id
                    
        if best_agent_id:
            return best_agent_id
            
        # Strategy 3: Simply return first available agent
        if available_agents:
            return next(iter(available_agents.keys()))
            
        return None
        
    def record_execution_result(
        self, agent_id: str, task: Task, success: bool, execution_time: float
    ) -> None:
        """Record task execution results for future selection decisions.
        
        Args:
            agent_id: The agent that executed the task
            task: The executed task
            success: Whether execution was successful
            execution_time: Time taken to execute
        """
        self.skill_matrix.update_agent_performance(agent_id, success, execution_time) 