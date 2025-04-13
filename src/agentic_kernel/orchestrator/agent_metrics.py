"""Agent performance metrics collection and analysis system.

This module provides a comprehensive system for collecting, storing, analyzing,
and visualizing agent performance metrics. It tracks various performance indicators
for agents, including execution time, success rate, resource usage, and custom
metrics defined by individual agents.
"""

import logging
import statistics
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

from ..types import AgentType

logger = logging.getLogger(__name__)


class AgentMetric:
    """Represents a single metric measurement for an agent."""

    def __init__(
        self,
        name: str,
        value: float | int | str | bool,
        timestamp: datetime | None = None,
        tags: dict[str, str] | None = None,
    ):
        """Initialize a metric measurement.

        Args:
            name: Name of the metric
            value: Value of the metric
            timestamp: When the metric was recorded (defaults to now)
            tags: Additional contextual tags for the metric
        """
        self.name = name
        self.value = value
        self.timestamp = timestamp or datetime.now()
        self.tags = tags or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert the metric to a dictionary representation."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


class AgentMetricsCollector:
    """Collects and analyzes agent performance metrics."""

    def __init__(self, max_history_per_agent: int = 1000):
        """Initialize the metrics collector.

        Args:
            max_history_per_agent: Maximum number of metrics to store per agent
        """
        self.max_history_per_agent = max_history_per_agent
        self.metrics: dict[str, list[AgentMetric]] = defaultdict(list)
        self.agent_types: dict[str, AgentType] = {}
        self.start_times: dict[str, float] = {}
        self.active_tasks: dict[str, dict[str, Any]] = {}

    def register_agent(self, agent_id: str, agent_type: AgentType) -> None:
        """Register an agent with the metrics collector.

        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of the agent
        """
        self.agent_types[agent_id] = agent_type
        if agent_id not in self.metrics:
            self.metrics[agent_id] = []

    def start_task(self, agent_id: str, task_id: str, task_info: dict[str, Any]) -> None:
        """Record the start of a task for an agent.

        Args:
            agent_id: Agent executing the task
            task_id: Unique identifier for the task
            task_info: Additional information about the task
        """
        self.start_times[f"{agent_id}:{task_id}"] = time.time()
        self.active_tasks[f"{agent_id}:{task_id}"] = task_info

    def end_task(
        self, agent_id: str, task_id: str, result: dict[str, Any],
    ) -> dict[str, Any]:
        """Record the end of a task and collect metrics.

        Args:
            agent_id: Agent that executed the task
            task_id: Unique identifier for the task
            result: Result of the task execution

        Returns:
            Dictionary of collected metrics
        """
        task_key = f"{agent_id}:{task_id}"
        
        # Calculate execution time
        execution_time = 0.0
        if task_key in self.start_times:
            execution_time = time.time() - self.start_times[task_key]
            del self.start_times[task_key]
        
        # Get task info
        task_info = {}
        if task_key in self.active_tasks:
            task_info = self.active_tasks[task_key]
            del self.active_tasks[task_key]
        
        # Collect basic metrics
        metrics = {
            "execution_time": execution_time,
            "success": result.get("status") == "success",
        }
        
        # Add any metrics from the result
        if "metrics" in result:
            metrics.update(result["metrics"])
        
        # Record all metrics
        timestamp = datetime.now()
        tags = {
            "task_id": task_id,
            "task_type": task_info.get("type", "unknown"),
        }
        
        for name, value in metrics.items():
            self.add_metric(agent_id, name, value, timestamp, tags)
        
        return metrics

    def add_metric(
        self,
        agent_id: str,
        name: str,
        value: float | int | str | bool,
        timestamp: datetime | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Add a metric measurement for an agent.

        Args:
            agent_id: Agent the metric is for
            name: Name of the metric
            value: Value of the metric
            timestamp: When the metric was recorded (defaults to now)
            tags: Additional contextual tags for the metric
        """
        metric = AgentMetric(name, value, timestamp, tags)
        
        # Add to metrics list, maintaining max history size
        self.metrics[agent_id].append(metric)
        if len(self.metrics[agent_id]) > self.max_history_per_agent:
            self.metrics[agent_id] = self.metrics[agent_id][-self.max_history_per_agent:]

    def get_agent_metrics(
        self, agent_id: str, metric_name: str | None = None, limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get metrics for a specific agent.

        Args:
            agent_id: Agent to get metrics for
            metric_name: Optional filter for specific metric
            limit: Maximum number of metrics to return

        Returns:
            List of metric dictionaries
        """
        if agent_id not in self.metrics:
            return []
        
        filtered_metrics = [
            m.to_dict() 
            for m in self.metrics[agent_id] 
            if metric_name is None or m.name == metric_name
        ]
        
        # Return most recent metrics first
        return sorted(
            filtered_metrics, 
            key=lambda m: m["timestamp"], 
            reverse=True,
        )[:limit]

    def get_agent_metric_summary(
        self, agent_id: str, metric_name: str,
    ) -> dict[str, Any]:
        """Get statistical summary of a metric for an agent.

        Args:
            agent_id: Agent to get metrics for
            metric_name: Name of the metric to summarize

        Returns:
            Dictionary with statistical summary
        """
        if agent_id not in self.metrics:
            return {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "median": None,
            }
        
        # Filter metrics by name and ensure they're numeric
        values = [
            float(m.value) 
            for m in self.metrics[agent_id] 
            if m.name == metric_name and isinstance(m.value, (int, float))
        ]
        
        if not values:
            return {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "median": None,
            }
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "recent": values[-1] if values else None,
        }

    def get_all_agent_summaries(self) -> dict[str, dict[str, Any]]:
        """Get performance summaries for all agents.

        Returns:
            Dictionary mapping agent IDs to their performance summaries
        """
        summaries = {}
        
        for agent_id in self.metrics:
            # Get all unique metric names for this agent
            metric_names = {m.name for m in self.metrics[agent_id]}
            
            # Calculate success rate
            success_values = [
                m.value 
                for m in self.metrics[agent_id] 
                if m.name == "success" and isinstance(m.value, bool)
            ]
            success_rate = (
                sum(1 for v in success_values if v) / len(success_values)
                if success_values
                else None
            )
            
            # Get execution time statistics
            execution_time_summary = self.get_agent_metric_summary(
                agent_id, "execution_time",
            )
            
            # Build summary
            summaries[agent_id] = {
                "agent_type": self.agent_types.get(agent_id, "unknown"),
                "success_rate": success_rate,
                "execution_time": execution_time_summary,
                "task_count": len(set(
                    m.tags.get("task_id") 
                    for m in self.metrics[agent_id] 
                    if "task_id" in m.tags
                )),
                "available_metrics": list(metric_names),
            }
        
        return summaries

    def compare_agents(
        self, agent_ids: list[str], metric_name: str,
    ) -> dict[str, dict[str, Any]]:
        """Compare multiple agents based on a specific metric.

        Args:
            agent_ids: List of agent IDs to compare
            metric_name: Metric to use for comparison

        Returns:
            Dictionary mapping agent IDs to their metric summaries
        """
        return {
            agent_id: self.get_agent_metric_summary(agent_id, metric_name)
            for agent_id in agent_ids
            if agent_id in self.metrics
        }

    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health metrics.

        Returns:
            Dictionary with system health indicators
        """
        # Count active agents and tasks
        active_agents = set()
        for task_key in self.active_tasks:
            agent_id = task_key.split(":")[0]
            active_agents.add(agent_id)
        
        # Calculate overall success rate
        all_success_metrics = []
        for agent_metrics in self.metrics.values():
            all_success_metrics.extend([
                m.value 
                for m in agent_metrics 
                if m.name == "success" and isinstance(m.value, bool)
            ])
        
        success_rate = (
            sum(1 for v in all_success_metrics if v) / len(all_success_metrics)
            if all_success_metrics
            else None
        )
        
        return {
            "active_agents": len(active_agents),
            "active_tasks": len(self.active_tasks),
            "registered_agents": len(self.agent_types),
            "overall_success_rate": success_rate,
            "metrics_collected": sum(len(metrics) for metrics in self.metrics.values()),
        }

    def export_metrics(self, format_type: str = "json") -> dict[str, Any]:
        """Export all metrics in a specified format.

        Args:
            format_type: Format to export metrics in (json, csv, etc.)

        Returns:
            Dictionary with exported metrics data
        """
        if format_type != "json":
            raise ValueError(f"Unsupported export format: {format_type}")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system_health": self.get_system_health(),
            "agent_summaries": self.get_all_agent_summaries(),
            "detailed_metrics": {
                agent_id: [m.to_dict() for m in agent_metrics]
                for agent_id, agent_metrics in self.metrics.items()
            },
        }