"""Feedback loop system for agent learning and improvement.

This module implements a feedback loop system that allows agents to learn from
feedback and improve their performance over time. It provides mechanisms for
collecting, storing, analyzing, and applying feedback to adjust agent behavior.

Key features:
1. Feedback collection and storage
2. Feedback analysis and insight extraction
3. Learning mechanisms for behavior adjustment
4. Performance tracking and improvement metrics
"""

import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Generic

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class FeedbackCategory(Enum):
    """Categories of feedback that can be provided to agents."""

    PERFORMANCE = "performance"  # Feedback on agent performance (speed, efficiency)
    QUALITY = "quality"  # Feedback on output quality
    BEHAVIOR = "behavior"  # Feedback on agent behavior or interaction style
    ACCURACY = "accuracy"  # Feedback on factual accuracy
    RELEVANCE = "relevance"  # Feedback on relevance of responses
    CREATIVITY = "creativity"  # Feedback on creative aspects
    REASONING = "reasoning"  # Feedback on reasoning process
    COLLABORATION = "collaboration"  # Feedback on collaborative behavior
    COMMUNICATION = "communication"  # Feedback on communication style
    OTHER = "other"  # Other types of feedback


class FeedbackSeverity(Enum):
    """Severity levels for feedback."""

    CRITICAL = "critical"  # Critical issues that must be addressed immediately
    HIGH = "high"  # Important issues that should be addressed soon
    MEDIUM = "medium"  # Issues that should be addressed when possible
    LOW = "low"  # Minor issues that can be addressed later
    POSITIVE = "positive"  # Positive feedback, no issues


class FeedbackEntry(BaseModel):
    """Model for a single feedback entry.

    Attributes:
        feedback_id: Unique identifier for the feedback
        agent_id: ID of the agent receiving feedback
        source_id: ID of the agent or entity providing feedback
        category: Category of the feedback
        severity: Severity level of the feedback
        rating: Numerical rating (0.0-1.0, higher is better)
        description: Detailed description of the feedback
        improvement_suggestions: Suggestions for improvement
        context: Context in which the feedback applies
        timestamp: When the feedback was created
        task_id: Optional ID of the task related to the feedback
        conversation_id: Optional ID of the conversation related to the feedback
        metadata: Additional feedback metadata
    """

    feedback_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    source_id: str
    category: FeedbackCategory
    severity: FeedbackSeverity
    rating: float
    description: str
    improvement_suggestions: Optional[List[str]] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    task_id: Optional[str] = None
    conversation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("rating")
    def validate_rating(cls, v: float) -> float:
        """Validate that rating is between 0.0 and 1.0."""
        if v < 0.0 or v > 1.0:
            raise ValueError("Rating must be between 0.0 and 1.0")
        return v


class FeedbackStore:
    """Storage for feedback entries.

    This class provides methods for storing, retrieving, and querying feedback
    entries. It serves as the persistence layer for the feedback loop system.

    Attributes:
        feedback_entries: Dictionary mapping feedback IDs to feedback entries
        agent_feedback: Dictionary mapping agent IDs to sets of feedback IDs
    """

    def __init__(self):
        """Initialize the feedback store."""
        self.feedback_entries: Dict[str, FeedbackEntry] = {}
        self.agent_feedback: Dict[str, Set[str]] = {}

    def add_feedback(self, feedback: FeedbackEntry) -> str:
        """Add a feedback entry to the store.

        Args:
            feedback: The feedback entry to add

        Returns:
            The ID of the added feedback entry
        """
        # Store the feedback entry
        self.feedback_entries[feedback.feedback_id] = feedback

        # Update the agent feedback index
        if feedback.agent_id not in self.agent_feedback:
            self.agent_feedback[feedback.agent_id] = set()
        self.agent_feedback[feedback.agent_id].add(feedback.feedback_id)

        logger.info(f"Added feedback {feedback.feedback_id} for agent {feedback.agent_id}")
        return feedback.feedback_id

    def get_feedback(self, feedback_id: str) -> Optional[FeedbackEntry]:
        """Get a feedback entry by ID.

        Args:
            feedback_id: ID of the feedback entry to retrieve

        Returns:
            The feedback entry, or None if not found
        """
        return self.feedback_entries.get(feedback_id)

    def get_agent_feedback(
        self, 
        agent_id: str,
        category: Optional[FeedbackCategory] = None,
        severity: Optional[FeedbackSeverity] = None,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        task_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> List[FeedbackEntry]:
        """Get feedback entries for an agent with optional filtering.

        Args:
            agent_id: ID of the agent to get feedback for
            category: Optional category to filter by
            severity: Optional severity to filter by
            min_rating: Optional minimum rating to filter by
            max_rating: Optional maximum rating to filter by
            start_time: Optional start time to filter by
            end_time: Optional end time to filter by
            task_id: Optional task ID to filter by
            conversation_id: Optional conversation ID to filter by

        Returns:
            List of feedback entries matching the criteria
        """
        if agent_id not in self.agent_feedback:
            return []

        # Get all feedback IDs for the agent
        feedback_ids = self.agent_feedback[agent_id]

        # Filter feedback entries
        result = []
        for feedback_id in feedback_ids:
            feedback = self.feedback_entries[feedback_id]

            # Apply filters
            if category and feedback.category != category:
                continue
            if severity and feedback.severity != severity:
                continue
            if min_rating is not None and feedback.rating < min_rating:
                continue
            if max_rating is not None and feedback.rating > max_rating:
                continue
            if start_time and feedback.timestamp < start_time:
                continue
            if end_time and feedback.timestamp > end_time:
                continue
            if task_id and feedback.task_id != task_id:
                continue
            if conversation_id and feedback.conversation_id != conversation_id:
                continue

            result.append(feedback)

        # Sort by timestamp (newest first)
        result.sort(key=lambda f: f.timestamp, reverse=True)

        return result


class FeedbackInsight(BaseModel):
    """Model for an insight derived from feedback analysis.

    Attributes:
        insight_id: Unique identifier for the insight
        agent_id: ID of the agent the insight applies to
        category: Category of the insight
        description: Description of the insight
        confidence: Confidence level in the insight (0.0-1.0)
        improvement_actions: Suggested actions for improvement
        source_feedback: IDs of feedback entries that led to this insight
        timestamp: When the insight was created
        metadata: Additional insight metadata
    """

    insight_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    category: FeedbackCategory
    description: str
    confidence: float
    improvement_actions: List[str]
    source_feedback: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("confidence")
    def validate_confidence(cls, v: float) -> float:
        """Validate that confidence is between 0.0 and 1.0."""
        if v < 0.0 or v > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class FeedbackAnalyzer:
    """Analyzer for extracting insights from feedback.

    This class provides methods for analyzing feedback entries and extracting
    actionable insights that can be used to improve agent performance.

    Attributes:
        feedback_store: Reference to the feedback store
        insights: Dictionary mapping insight IDs to insights
        agent_insights: Dictionary mapping agent IDs to sets of insight IDs
    """

    def __init__(self, feedback_store: FeedbackStore):
        """Initialize the feedback analyzer.

        Args:
            feedback_store: Reference to the feedback store
        """
        self.feedback_store = feedback_store
        self.insights: Dict[str, FeedbackInsight] = {}
        self.agent_insights: Dict[str, Set[str]] = {}

    def analyze_feedback(
        self, agent_id: str, feedback_ids: Optional[List[str]] = None
    ) -> List[FeedbackInsight]:
        """Analyze feedback for an agent and generate insights.

        Args:
            agent_id: ID of the agent to analyze feedback for
            feedback_ids: Optional list of specific feedback IDs to analyze

        Returns:
            List of insights generated from the feedback
        """
        # Get feedback entries to analyze
        if feedback_ids:
            feedback_entries = [
                self.feedback_store.get_feedback(fid) 
                for fid in feedback_ids
                if self.feedback_store.get_feedback(fid) is not None
            ]
        else:
            feedback_entries = self.feedback_store.get_agent_feedback(agent_id)

        if not feedback_entries:
            return []

        # Group feedback by category
        feedback_by_category: Dict[FeedbackCategory, List[FeedbackEntry]] = {}
        for entry in feedback_entries:
            if entry.category not in feedback_by_category:
                feedback_by_category[entry.category] = []
            feedback_by_category[entry.category].append(entry)

        # Generate insights for each category
        insights = []
        for category, entries in feedback_by_category.items():
            # Skip categories with too few entries
            if len(entries) < 2:
                continue

            # Calculate average rating
            avg_rating = sum(entry.rating for entry in entries) / len(entries)

            # Determine if this is a strength or weakness
            is_strength = avg_rating >= 0.7

            # Collect improvement suggestions
            all_suggestions = []
            for entry in entries:
                if entry.improvement_suggestions:
                    all_suggestions.extend(entry.improvement_suggestions)

            # Create a description based on the feedback
            if is_strength:
                description = f"Strong performance in {category.value} with average rating of {avg_rating:.2f}"
            else:
                description = f"Needs improvement in {category.value} with average rating of {avg_rating:.2f}"

            # Create improvement actions
            if is_strength:
                improvement_actions = ["Maintain current approach", "Share best practices with other agents"]
            else:
                # Use collected suggestions or generic ones if none available
                if all_suggestions:
                    improvement_actions = list(set(all_suggestions))[:5]  # Take up to 5 unique suggestions
                else:
                    improvement_actions = [f"Review and improve {category.value} capabilities"]

            # Create the insight
            insight = FeedbackInsight(
                agent_id=agent_id,
                category=category,
                description=description,
                confidence=min(0.5 + (len(entries) / 10), 0.95),  # Higher confidence with more entries, max 0.95
                improvement_actions=improvement_actions,
                source_feedback=[entry.feedback_id for entry in entries],
            )

            # Store the insight
            self.insights[insight.insight_id] = insight
            if agent_id not in self.agent_insights:
                self.agent_insights[agent_id] = set()
            self.agent_insights[agent_id].add(insight.insight_id)

            insights.append(insight)

        return insights

    def get_agent_insights(
        self, 
        agent_id: str,
        category: Optional[FeedbackCategory] = None,
        min_confidence: Optional[float] = None,
    ) -> List[FeedbackInsight]:
        """Get insights for an agent with optional filtering.

        Args:
            agent_id: ID of the agent to get insights for
            category: Optional category to filter by
            min_confidence: Optional minimum confidence to filter by

        Returns:
            List of insights matching the criteria
        """
        if agent_id not in self.agent_insights:
            return []

        # Get all insight IDs for the agent
        insight_ids = self.agent_insights[agent_id]

        # Filter insights
        result = []
        for insight_id in insight_ids:
            insight = self.insights[insight_id]

            # Apply filters
            if category and insight.category != category:
                continue
            if min_confidence is not None and insight.confidence < min_confidence:
                continue

            result.append(insight)

        # Sort by confidence (highest first)
        result.sort(key=lambda i: i.confidence, reverse=True)

        return result


class LearningStrategy(Enum):
    """Learning strategies for adjusting agent behavior."""

    REINFORCEMENT = "reinforcement"  # Reinforce behaviors with positive feedback
    CORRECTION = "correction"  # Correct behaviors with negative feedback
    ADAPTIVE = "adaptive"  # Adapt behavior based on all feedback
    THRESHOLD = "threshold"  # Change behavior when feedback crosses a threshold
    WEIGHTED = "weighted"  # Weight behavior adjustments by feedback confidence


class AgentAdjustment(BaseModel):
    """Model for an adjustment to agent behavior.

    Attributes:
        adjustment_id: Unique identifier for the adjustment
        agent_id: ID of the agent the adjustment applies to
        category: Category of the adjustment
        parameter: Parameter to adjust
        old_value: Previous value of the parameter
        new_value: New value of the parameter
        confidence: Confidence level in the adjustment (0.0-1.0)
        source_insights: IDs of insights that led to this adjustment
        timestamp: When the adjustment was created
        applied: Whether the adjustment has been applied
        result: Optional result of applying the adjustment
    """

    adjustment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    category: FeedbackCategory
    parameter: str
    old_value: Any
    new_value: Any
    confidence: float
    source_insights: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    applied: bool = False
    result: Optional[Dict[str, Any]] = None

    @validator("confidence")
    def validate_confidence(cls, v: float) -> float:
        """Validate that confidence is between 0.0 and 1.0."""
        if v < 0.0 or v > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class FeedbackLearner:
    """Learner for adjusting agent behavior based on feedback.

    This class provides methods for generating and applying adjustments to
    agent behavior based on insights derived from feedback analysis.

    Attributes:
        feedback_analyzer: Reference to the feedback analyzer
        adjustments: Dictionary mapping adjustment IDs to adjustments
        agent_adjustments: Dictionary mapping agent IDs to sets of adjustment IDs
        learning_strategy: The learning strategy to use
    """

    def __init__(
        self, 
        feedback_analyzer: FeedbackAnalyzer,
        learning_strategy: LearningStrategy = LearningStrategy.ADAPTIVE
    ):
        """Initialize the feedback learner.

        Args:
            feedback_analyzer: Reference to the feedback analyzer
            learning_strategy: The learning strategy to use
        """
        self.feedback_analyzer = feedback_analyzer
        self.adjustments: Dict[str, AgentAdjustment] = {}
        self.agent_adjustments: Dict[str, Set[str]] = {}
        self.learning_strategy = learning_strategy

    def generate_adjustments(
        self, 
        agent_id: str,
        agent_parameters: Dict[str, Any],
        insight_ids: Optional[List[str]] = None
    ) -> List[AgentAdjustment]:
        """Generate adjustments for an agent based on insights.

        Args:
            agent_id: ID of the agent to generate adjustments for
            agent_parameters: Current parameters of the agent
            insight_ids: Optional list of specific insight IDs to use

        Returns:
            List of adjustments generated from the insights
        """
        # Get insights to use
        if insight_ids:
            insights = [
                self.feedback_analyzer.insights[iid] 
                for iid in insight_ids
                if iid in self.feedback_analyzer.insights
            ]
        else:
            insights = self.feedback_analyzer.get_agent_insights(
                agent_id, min_confidence=0.6
            )

        if not insights:
            return []

        # Generate adjustments based on the learning strategy
        adjustments = []

        if self.learning_strategy == LearningStrategy.ADAPTIVE:
            # Generate adjustments for each insight
            for insight in insights:
                # Skip insights with low confidence
                if insight.confidence < 0.6:
                    continue

                # Determine parameters to adjust based on category
                parameters_to_adjust = self._get_parameters_for_category(
                    insight.category, agent_parameters
                )

                for param, adjustment_fn in parameters_to_adjust.items():
                    # Skip if parameter doesn't exist
                    if param not in agent_parameters:
                        continue

                    old_value = agent_parameters[param]
                    new_value = adjustment_fn(old_value, insight)

                    # Skip if no change
                    if new_value == old_value:
                        continue

                    # Create the adjustment
                    adjustment = AgentAdjustment(
                        agent_id=agent_id,
                        category=insight.category,
                        parameter=param,
                        old_value=old_value,
                        new_value=new_value,
                        confidence=insight.confidence,
                        source_insights=[insight.insight_id],
                    )

                    # Store the adjustment
                    self.adjustments[adjustment.adjustment_id] = adjustment
                    if agent_id not in self.agent_adjustments:
                        self.agent_adjustments[agent_id] = set()
                    self.agent_adjustments[agent_id].add(adjustment.adjustment_id)

                    adjustments.append(adjustment)

        return adjustments

    def _get_parameters_for_category(
        self, category: FeedbackCategory, agent_parameters: Dict[str, Any]
    ) -> Dict[str, Callable[[Any, FeedbackInsight], Any]]:
        """Get parameters to adjust for a feedback category.

        Args:
            category: The feedback category
            agent_parameters: Current parameters of the agent

        Returns:
            Dictionary mapping parameter names to adjustment functions
        """
        # Define adjustment functions for different categories
        if category == FeedbackCategory.PERFORMANCE:
            return {
                "response_time_target": lambda v, i: max(v * 0.9, 0.1) if i.confidence > 0.7 else v,
                "max_tokens_per_response": lambda v, i: int(v * 1.1) if i.confidence > 0.7 else v,
            }
        elif category == FeedbackCategory.QUALITY:
            return {
                "quality_threshold": lambda v, i: min(v * 1.1, 0.95) if i.confidence > 0.7 else v,
                "review_frequency": lambda v, i: max(v * 0.9, 0.1) if i.confidence > 0.7 else v,
            }
        elif category == FeedbackCategory.ACCURACY:
            return {
                "fact_checking_enabled": lambda v, i: True if i.confidence > 0.7 and not v else v,
                "confidence_threshold": lambda v, i: min(v * 1.1, 0.95) if i.confidence > 0.7 else v,
            }
        elif category == FeedbackCategory.COMMUNICATION:
            return {
                "verbosity": lambda v, i: min(v * 1.1, 1.0) if "too brief" in i.description.lower() else 
                              max(v * 0.9, 0.1) if "too verbose" in i.description.lower() else v,
                "formality": lambda v, i: min(v * 1.1, 1.0) if "too informal" in i.description.lower() else 
                             max(v * 0.9, 0.1) if "too formal" in i.description.lower() else v,
            }

        # Default: no parameters to adjust
        return {}

    def apply_adjustment(
        self, adjustment_id: str, agent_parameters: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Apply an adjustment to agent parameters.

        Args:
            adjustment_id: ID of the adjustment to apply
            agent_parameters: Current parameters of the agent

        Returns:
            Tuple containing:
            - Boolean indicating if the adjustment was applied
            - Updated agent parameters
        """
        if adjustment_id not in self.adjustments:
            return False, agent_parameters

        adjustment = self.adjustments[adjustment_id]

        # Skip if already applied
        if adjustment.applied:
            return False, agent_parameters

        # Apply the adjustment
        if adjustment.parameter in agent_parameters:
            agent_parameters[adjustment.parameter] = adjustment.new_value

            # Mark as applied
            adjustment.applied = True
            adjustment.result = {"status": "applied", "timestamp": datetime.utcnow().isoformat()}

            logger.info(
                f"Applied adjustment {adjustment_id} to agent {adjustment.agent_id}: "
                f"{adjustment.parameter} = {adjustment.new_value}"
            )

            return True, agent_parameters
        else:
            # Parameter doesn't exist
            adjustment.result = {"status": "failed", "reason": "parameter_not_found"}
            return False, agent_parameters

    def get_agent_adjustments(
        self, 
        agent_id: str,
        category: Optional[FeedbackCategory] = None,
        min_confidence: Optional[float] = None,
        applied_only: bool = False,
    ) -> List[AgentAdjustment]:
        """Get adjustments for an agent with optional filtering.

        Args:
            agent_id: ID of the agent to get adjustments for
            category: Optional category to filter by
            min_confidence: Optional minimum confidence to filter by
            applied_only: Whether to only include applied adjustments

        Returns:
            List of adjustments matching the criteria
        """
        if agent_id not in self.agent_adjustments:
            return []

        # Get all adjustment IDs for the agent
        adjustment_ids = self.agent_adjustments[agent_id]

        # Filter adjustments
        result = []
        for adjustment_id in adjustment_ids:
            adjustment = self.adjustments[adjustment_id]

            # Apply filters
            if category and adjustment.category != category:
                continue
            if min_confidence is not None and adjustment.confidence < min_confidence:
                continue
            if applied_only and not adjustment.applied:
                continue

            result.append(adjustment)

        # Sort by confidence (highest first)
        result.sort(key=lambda a: a.confidence, reverse=True)

        return result


class PerformanceMetric(BaseModel):
    """Model for tracking agent performance metrics.

    Attributes:
        metric_id: Unique identifier for the metric
        agent_id: ID of the agent the metric applies to
        category: Category of the metric
        name: Name of the metric
        value: Value of the metric
        timestamp: When the metric was recorded
        metadata: Additional metric metadata
    """

    metric_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    category: FeedbackCategory
    name: str
    value: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FeedbackManager:
    """Manager for coordinating the feedback loop process.

    This class provides a high-level interface for the feedback loop system,
    coordinating the collection, analysis, and application of feedback to
    improve agent performance.

    Attributes:
        feedback_store: The feedback store
        feedback_analyzer: The feedback analyzer
        feedback_learner: The feedback learner
        performance_metrics: Dictionary mapping metric IDs to performance metrics
        agent_metrics: Dictionary mapping agent IDs to sets of metric IDs
    """

    def __init__(
        self,
        learning_strategy: LearningStrategy = LearningStrategy.ADAPTIVE
    ):
        """Initialize the feedback manager.

        Args:
            learning_strategy: The learning strategy to use
        """
        self.feedback_store = FeedbackStore()
        self.feedback_analyzer = FeedbackAnalyzer(self.feedback_store)
        self.feedback_learner = FeedbackLearner(
            self.feedback_analyzer, learning_strategy
        )
        self.performance_metrics: Dict[str, PerformanceMetric] = {}
        self.agent_metrics: Dict[str, Set[str]] = {}

    def process_feedback(
        self, 
        feedback: FeedbackEntry,
        agent_parameters: Dict[str, Any]
    ) -> Tuple[List[FeedbackInsight], List[AgentAdjustment], Dict[str, Any]]:
        """Process a feedback entry and update agent behavior.

        This method implements the complete feedback loop:
        1. Store the feedback
        2. Analyze the feedback to generate insights
        3. Generate adjustments based on the insights
        4. Apply the adjustments to agent parameters

        Args:
            feedback: The feedback entry to process
            agent_parameters: Current parameters of the agent

        Returns:
            Tuple containing:
            - List of insights generated from the feedback
            - List of adjustments generated from the insights
            - Updated agent parameters
        """
        # Store the feedback
        self.feedback_store.add_feedback(feedback)

        # Analyze the feedback
        insights = self.feedback_analyzer.analyze_feedback(
            feedback.agent_id, [feedback.feedback_id]
        )

        # Generate adjustments
        adjustments = self.feedback_learner.generate_adjustments(
            feedback.agent_id,
            agent_parameters,
            [insight.insight_id for insight in insights]
        )

        # Apply adjustments
        updated_parameters = agent_parameters.copy()
        for adjustment in adjustments:
            applied, updated_parameters = self.feedback_learner.apply_adjustment(
                adjustment.adjustment_id, updated_parameters
            )

        # Record performance metric
        self.record_performance_metric(
            agent_id=feedback.agent_id,
            category=feedback.category,
            name=f"{feedback.category.value}_rating",
            value=feedback.rating,
            metadata={"feedback_id": feedback.feedback_id}
        )

        return insights, adjustments, updated_parameters

    def record_performance_metric(
        self,
        agent_id: str,
        category: FeedbackCategory,
        name: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record a performance metric for an agent.

        Args:
            agent_id: ID of the agent to record the metric for
            category: Category of the metric
            name: Name of the metric
            value: Value of the metric
            metadata: Additional metric metadata

        Returns:
            The ID of the recorded metric
        """
        metric = PerformanceMetric(
            agent_id=agent_id,
            category=category,
            name=name,
            value=value,
            metadata=metadata or {},
        )

        # Store the metric
        self.performance_metrics[metric.metric_id] = metric
        if agent_id not in self.agent_metrics:
            self.agent_metrics[agent_id] = set()
        self.agent_metrics[agent_id].add(metric.metric_id)

        return metric.metric_id

    def get_agent_performance(
        self,
        agent_id: str,
        category: Optional[FeedbackCategory] = None,
        metric_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, List[Tuple[datetime, float]]]:
        """Get performance metrics for an agent with optional filtering.

        Args:
            agent_id: ID of the agent to get metrics for
            category: Optional category to filter by
            metric_name: Optional metric name to filter by
            start_time: Optional start time to filter by
            end_time: Optional end time to filter by

        Returns:
            Dictionary mapping metric names to lists of (timestamp, value) tuples
        """
        if agent_id not in self.agent_metrics:
            return {}

        # Get all metric IDs for the agent
        metric_ids = self.agent_metrics[agent_id]

        # Filter metrics
        filtered_metrics = []
        for metric_id in metric_ids:
            metric = self.performance_metrics[metric_id]

            # Apply filters
            if category and metric.category != category:
                continue
            if metric_name and metric.name != metric_name:
                continue
            if start_time and metric.timestamp < start_time:
                continue
            if end_time and metric.timestamp > end_time:
                continue

            filtered_metrics.append(metric)

        # Group metrics by name
        metrics_by_name: Dict[str, List[Tuple[datetime, float]]] = {}
        for metric in filtered_metrics:
            if metric.name not in metrics_by_name:
                metrics_by_name[metric.name] = []
            metrics_by_name[metric.name].append((metric.timestamp, metric.value))

        # Sort each list by timestamp
        for name, metrics in metrics_by_name.items():
            metrics.sort(key=lambda m: m[0])

        return metrics_by_name

    def get_performance_trend(
        self,
        agent_id: str,
        metric_name: str,
        window_size: int = 5,
    ) -> Optional[float]:
        """Calculate the trend of a performance metric over time.

        Args:
            agent_id: ID of the agent to get the trend for
            metric_name: Name of the metric to analyze
            window_size: Number of most recent metrics to consider

        Returns:
            Float indicating the trend (positive = improving, negative = declining),
            or None if not enough data points
        """
        # Get metrics for the agent and metric name
        metrics = self.get_agent_performance(agent_id, metric_name=metric_name)

        if metric_name not in metrics or len(metrics[metric_name]) < window_size:
            return None

        # Get the most recent metrics
        recent_metrics = metrics[metric_name][-window_size:]

        # Calculate the trend (simple linear regression slope)
        x = list(range(len(recent_metrics)))
        y = [m[1] for m in recent_metrics]

        # Calculate the slope using the formula:
        # slope = (n*sum(xy) - sum(x)*sum(y)) / (n*sum(x^2) - sum(x)^2)
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x_i * y_i for x_i, y_i in zip(x, y))
        sum_x_squared = sum(x_i * x_i for x_i in x)

        try:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x * sum_x)
            return slope
        except ZeroDivisionError:
            return None
