"""Metrics collection and reporting functionality for the orchestrator.

This module provides the MetricsManager class, which is responsible for
collecting, aggregating, and reporting metrics about agent performance
and system health.
"""

import logging
from typing import Any

from .agent_metrics import AgentMetricsCollector

logger = logging.getLogger(__name__)


class MetricsManager:
    """Manages metrics collection and reporting.

    This class is responsible for:
    1. Collecting agent metrics
    2. Generating metric summaries
    3. Providing system health information
    4. Exporting metrics data

    Attributes:
        metrics_collector: Component for collecting agent metrics
    """

    def __init__(self, metrics_collector: AgentMetricsCollector | None = None):
        """Initialize the metrics manager.

        Args:
            metrics_collector: Optional metrics collector component
        """
        self.metrics_collector = metrics_collector or AgentMetricsCollector()

    def register_agent(self, agent_id: str, agent_type: str) -> None:
        """Register an agent for metrics collection.

        Args:
            agent_id: ID of the agent
            agent_type: Type of the agent
        """
        self.metrics_collector.register_agent(agent_id, agent_type)
        logger.info(f"Registered agent {agent_id} ({agent_type}) for metrics collection")

    def record_agent_metric(
        self, agent_id: str, metric_name: str, value: Any, context: dict[str, Any] | None = None,
    ) -> None:
        """Record a metric for an agent.

        Args:
            agent_id: ID of the agent
            metric_name: Name of the metric
            value: Value of the metric
            context: Optional context information
        """
        self.metrics_collector.record_metric(
            agent_id=agent_id,
            metric_name=metric_name,
            value=value,
            context=context or {},
        )

    def get_agent_metrics(
        self, agent_id: str, metric_name: str | None = None, limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get performance metrics for a specific agent.

        Args:
            agent_id: ID of the agent to get metrics for
            metric_name: Optional name of a specific metric to retrieve
            limit: Maximum number of metrics to return

        Returns:
            List of metric dictionaries
        """
        return self.metrics_collector.get_agent_metrics(agent_id, metric_name, limit)

    def get_agent_metric_summary(
        self, agent_id: str, metric_name: str,
    ) -> dict[str, Any]:
        """Get a statistical summary of a specific metric for an agent.

        Args:
            agent_id: ID of the agent to get metrics for
            metric_name: Name of the metric to summarize

        Returns:
            Dictionary with statistical summary
        """
        return self.metrics_collector.get_agent_metric_summary(agent_id, metric_name)

    def get_all_agent_summaries(self) -> dict[str, dict[str, Any]]:
        """Get performance summaries for all registered agents.

        Returns:
            Dictionary mapping agent IDs to their performance summaries
        """
        return self.metrics_collector.get_all_agent_summaries()

    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health metrics.

        Returns:
            Dictionary with system health indicators
        """
        return self.metrics_collector.get_system_health()

    def export_metrics(self, format_type: str = "json") -> dict[str, Any]:
        """Export all metrics in a specified format.

        Args:
            format_type: Format to export metrics in (currently only "json" is supported)

        Returns:
            Dictionary with exported metrics data
        """
        return self.metrics_collector.export_metrics(format_type)

    def get_workflow_metrics(
        self, workflow_id: str, execution_id: str | None = None,
    ) -> dict[str, Any]:
        """Get metrics for a specific workflow execution.

        Args:
            workflow_id: ID of the workflow
            execution_id: Optional ID of a specific execution

        Returns:
            Dictionary with workflow metrics
        """
        # This would typically query the workflow history for metrics
        # For now, we'll return a placeholder
        return {
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "status": "placeholder",
            "metrics": {},
        }

    def get_agent_performance_trend(
        self, agent_id: str, metric_name: str, window_size: int = 10,
    ) -> dict[str, Any]:
        """Get the trend of a specific metric for an agent over time.

        Args:
            agent_id: ID of the agent
            metric_name: Name of the metric to track
            window_size: Number of data points to include

        Returns:
            Dictionary with trend information
        """
        metrics = self.get_agent_metrics(agent_id, metric_name, window_size)
        
        if not metrics:
            return {
                "agent_id": agent_id,
                "metric_name": metric_name,
                "trend": "no_data",
                "data_points": [],
            }
            
        # Extract values and timestamps
        values = [metric.get("value", 0) for metric in metrics]
        timestamps = [metric.get("timestamp", "") for metric in metrics]
        
        # Calculate trend (simple linear trend)
        trend = "stable"
        if len(values) >= 3:
            first_half = sum(values[:len(values)//2]) / max(1, len(values)//2)
            second_half = sum(values[len(values)//2:]) / max(1, len(values) - len(values)//2)
            
            if second_half > first_half * 1.1:
                trend = "increasing"
            elif second_half < first_half * 0.9:
                trend = "decreasing"
                
        return {
            "agent_id": agent_id,
            "metric_name": metric_name,
            "trend": trend,
            "data_points": [
                {"value": value, "timestamp": timestamp}
                for value, timestamp in zip(values, timestamps, strict=False)
            ],
            "average": sum(values) / max(1, len(values)),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }