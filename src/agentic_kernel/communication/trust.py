"""Trust and reputation system for agent interactions.

This module implements a trust and reputation system for agent interactions,
allowing agents to maintain and update trust levels based on their interactions
with other agents.

Key features:
1. Trust level tracking
2. Reputation scoring
3. Trust decay over time
4. Trust-based decision making
5. Reputation-based agent selection
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TrustMetric(BaseModel):
    """Represents a trust metric for an agent interaction.
    
    Attributes:
        agent_id: ID of the agent being rated
        metric_type: Type of trust metric (e.g., 'reliability', 'competence')
        value: Trust value (0.0-1.0)
        weight: Weight of this metric in overall trust calculation
        timestamp: When the metric was recorded
    """
    
    agent_id: str
    metric_type: str
    value: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TrustHistory(BaseModel):
    """Represents the trust history for an agent.
    
    Attributes:
        agent_id: ID of the agent
        metrics: List of trust metrics
        last_updated: When the trust history was last updated
    """
    
    agent_id: str
    metrics: List[TrustMetric] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class TrustManager:
    """Manages trust and reputation for agent interactions.
    
    This class provides methods for:
    1. Recording trust metrics
    2. Calculating trust scores
    3. Managing trust decay
    4. Making trust-based decisions
    """
    
    def __init__(self, decay_rate: float = 0.1, min_trust: float = 0.1):
        """Initialize the trust manager.
        
        Args:
            decay_rate: Rate at which trust decays over time (0.0-1.0)
            min_trust: Minimum trust value to maintain
        """
        self.decay_rate = decay_rate
        self.min_trust = min_trust
        self.trust_history: Dict[str, TrustHistory] = {}
    
    def record_trust_metric(
        self,
        agent_id: str,
        metric_type: str,
        value: float,
        weight: float = 1.0,
    ) -> None:
        """Record a trust metric for an agent.
        
        Args:
            agent_id: ID of the agent
            metric_type: Type of trust metric
            value: Trust value (0.0-1.0)
            weight: Weight of this metric
        """
        if agent_id not in self.trust_history:
            self.trust_history[agent_id] = TrustHistory(agent_id=agent_id)
        
        metric = TrustMetric(
            agent_id=agent_id,
            metric_type=metric_type,
            value=value,
            weight=weight,
        )
        
        self.trust_history[agent_id].metrics.append(metric)
        self.trust_history[agent_id].last_updated = datetime.utcnow()
    
    def calculate_trust_score(self, agent_id: str) -> float:
        """Calculate the overall trust score for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Trust score (0.0-1.0)
        """
        if agent_id not in self.trust_history:
            return self.min_trust
        
        history = self.trust_history[agent_id]
        total_weight = 0.0
        weighted_sum = 0.0
        
        # Apply time decay to metrics
        current_time = datetime.utcnow()
        
        for metric in history.metrics:
            time_diff = (current_time - metric.timestamp).total_seconds()
            decay_factor = max(0.0, 1.0 - self.decay_rate * time_diff / 86400)  # Decay per day
            
            weighted_value = metric.value * metric.weight * decay_factor
            weighted_sum += weighted_value
            total_weight += metric.weight * decay_factor
        
        if total_weight == 0:
            return self.min_trust
        
        trust_score = weighted_sum / total_weight
        return max(self.min_trust, min(1.0, trust_score))
    
    def get_trust_metrics(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all trust metrics for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of trust metrics
        """
        if agent_id not in self.trust_history:
            return []
        
        return [
            {
                "metric_type": metric.metric_type,
                "value": metric.value,
                "weight": metric.weight,
                "timestamp": metric.timestamp.isoformat(),
            }
            for metric in self.trust_history[agent_id].metrics
        ]
    
    def should_trust_agent(
        self,
        agent_id: str,
        required_trust: float,
        metric_types: Optional[List[str]] = None,
    ) -> Tuple[bool, float]:
        """Determine if an agent should be trusted for a specific task.
        
        Args:
            agent_id: ID of the agent
            required_trust: Minimum required trust level
            metric_types: Specific metric types to consider
            
        Returns:
            Tuple of (should_trust, trust_score)
        """
        trust_score = self.calculate_trust_score(agent_id)
        
        if metric_types:
            # Calculate trust score only for specified metrics
            history = self.trust_history.get(agent_id)
            if not history:
                return False, self.min_trust
            
            total_weight = 0.0
            weighted_sum = 0.0
            
            for metric in history.metrics:
                if metric.metric_type in metric_types:
                    weighted_sum += metric.value * metric.weight
                    total_weight += metric.weight
            
            if total_weight > 0:
                trust_score = weighted_sum / total_weight
        
        return trust_score >= required_trust, trust_score
    
    def update_trust_based_on_interaction(
        self,
        agent_id: str,
        success: bool,
        interaction_type: str,
        weight: float = 1.0,
    ) -> None:
        """Update trust based on an interaction outcome.
        
        Args:
            agent_id: ID of the agent
            success: Whether the interaction was successful
            interaction_type: Type of interaction
            weight: Weight of this interaction
        """
        value = 1.0 if success else 0.0
        self.record_trust_metric(
            agent_id=agent_id,
            metric_type=f"{interaction_type}_success",
            value=value,
            weight=weight,
        )
    
    def get_most_trusted_agents(
        self,
        min_trust: float = 0.5,
        limit: Optional[int] = None,
    ) -> List[Tuple[str, float]]:
        """Get a list of the most trusted agents.
        
        Args:
            min_trust: Minimum trust level to consider
            limit: Maximum number of agents to return
            
        Returns:
            List of (agent_id, trust_score) tuples
        """
        agent_scores = [
            (agent_id, self.calculate_trust_score(agent_id))
            for agent_id in self.trust_history
        ]
        
        # Filter by minimum trust and sort by score
        filtered_scores = [
            (agent_id, score)
            for agent_id, score in agent_scores
            if score >= min_trust
        ]
        filtered_scores.sort(key=lambda x: x[1], reverse=True)
        
        if limit is not None:
            filtered_scores = filtered_scores[:limit]
        
        return filtered_scores 