"""
Feedback and performance metrics for agents.

This module contains classes and methods for handling feedback,
tracking performance metrics, and generating insights based on
agent performance.
"""

from typing import Any

from ...communication.feedback import (
    FeedbackCategory,
    FeedbackEntry,
    FeedbackManager,
    FeedbackSeverity,
    LearningStrategy,
)
from ...communication.message import Message, MessageType
from .base_agent import BaseAgent


class FeedbackMixin:
    """
    Mixin class providing feedback and performance tracking functionality for agents.
    
    This mixin provides methods for processing feedback, tracking performance
    metrics, and generating insights based on agent performance.
    """
    
    def _handle_feedback(self, message: Message) -> None:
        """
        Handle a feedback message.
        
        Args:
            message: The feedback message
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("FeedbackMixin must be used with BaseAgent")
            
        self.logger.info(f"Received feedback from {message.sender_id}")
        
        try:
            # Extract feedback details
            category = message.content.get("category", "general")
            rating = message.content.get("rating", 0.0)
            description = message.content.get("description", "")
            suggestions = message.content.get("improvement_suggestions", [])
            context = message.content.get("context", {})
            
            # Create feedback entry
            feedback = FeedbackEntry(
                category=FeedbackCategory(category),
                rating=float(rating),
                description=description,
                improvement_suggestions=suggestions,
                context=context,
                timestamp=message.timestamp,
                source=message.sender_id,
            )
            
            # Process the feedback
            self.process_feedback(feedback)
            
            # Send acknowledgment
            ack_message = self.protocol.create_message(
                sender_id=self.id,
                recipient_id=message.sender_id,
                message_type=MessageType.FEEDBACK_ACKNOWLEDGMENT,
                content={
                    "status": "received",
                    "message": "Feedback received and processed",
                },
                reference_message_id=message.message_id,
            )
            
            self.message_bus.send_message(ack_message)
            
        except Exception as e:
            self.logger.error(f"Error handling feedback: {str(e)}")
            
            # Send error response
            error_response = self.protocol.create_message(
                sender_id=self.id,
                recipient_id=message.sender_id,
                message_type=MessageType.FEEDBACK_ACKNOWLEDGMENT,
                content={
                    "status": "error",
                    "message": f"Error processing feedback: {str(e)}",
                },
                reference_message_id=message.message_id,
            )
            
            self.message_bus.send_message(error_response)

    def process_feedback(self, feedback: FeedbackEntry) -> None:
        """
        Process a feedback entry and update performance metrics.
        
        Args:
            feedback: The feedback entry to process
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("FeedbackMixin must be used with BaseAgent")
            
        # Initialize feedback manager if needed
        if not hasattr(self, "feedback_manager"):
            self.feedback_manager = FeedbackManager()
            
        # Record the feedback
        self.feedback_manager.record_feedback(feedback)
        
        # Log the feedback
        severity = "positive" if feedback.rating >= 0.7 else "neutral" if feedback.rating >= 0.4 else "negative"
        self.logger.info(
            f"Processed {severity} feedback in category '{feedback.category}': {feedback.description}",
        )
        
        # Apply learning strategy based on feedback category and rating
        if feedback.rating < 0.4:  # Negative feedback
            # For negative feedback, we might want to adjust behavior more aggressively
            learning_strategy = LearningStrategy.IMMEDIATE_ADJUSTMENT
            self.feedback_manager.apply_learning_strategy(
                feedback, learning_strategy,
            )
            
            # Log suggestions
            if feedback.improvement_suggestions:
                self.logger.info(
                    f"Improvement suggestions: {', '.join(feedback.improvement_suggestions)}",
                )
        elif feedback.rating >= 0.7:  # Positive feedback
            # For positive feedback, we might want to reinforce behavior
            learning_strategy = LearningStrategy.REINFORCEMENT
            self.feedback_manager.apply_learning_strategy(
                feedback, learning_strategy,
            )
        else:  # Neutral feedback
            # For neutral feedback, we might want to collect more data before adjusting
            learning_strategy = LearningStrategy.GRADUAL_ADJUSTMENT
            self.feedback_manager.apply_learning_strategy(
                feedback, learning_strategy,
            )

    def get_performance_metrics(
        self, 
        category: FeedbackCategory | None = None, 
        metric_name: str | None = None,
        window_size: int = 10,
    ) -> dict[str, Any]:
        """
        Get performance metrics based on feedback.
        
        Args:
            category: Optional category to filter metrics by
            metric_name: Optional specific metric to retrieve
            window_size: Number of recent feedback entries to consider
            
        Returns:
            Dictionary of performance metrics
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("FeedbackMixin must be used with BaseAgent")
            
        # Initialize feedback manager if needed
        if not hasattr(self, "feedback_manager"):
            self.feedback_manager = FeedbackManager()
            return {"status": "no_data", "message": "No feedback data available"}
            
        # Get metrics from feedback manager
        metrics = self.feedback_manager.get_performance_metrics(
            category=category,
            metric_name=metric_name,
            window_size=window_size,
        )
        
        # Add task execution metrics
        metrics.update({
            "tasks_received": self.tasks_received,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "completion_rate": self.tasks_completed / max(1, self.tasks_received),
            "avg_execution_time": sum(self.execution_times[-window_size:]) / max(1, len(self.execution_times[-window_size:])) if self.execution_times else 0,
        })
        
        return metrics

    def get_performance_trend(self, metric_name: str, window_size: int = 5) -> dict[str, Any]:
        """
        Get the trend of a specific performance metric over time.
        
        Args:
            metric_name: Name of the metric to track
            window_size: Number of time periods to include
            
        Returns:
            Dictionary with trend information
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("FeedbackMixin must be used with BaseAgent")
            
        # Initialize feedback manager if needed
        if not hasattr(self, "feedback_manager"):
            self.feedback_manager = FeedbackManager()
            return {"status": "no_data", "message": "No feedback data available"}
            
        # Get trend from feedback manager
        return self.feedback_manager.get_performance_trend(
            metric_name=metric_name,
            window_size=window_size,
        )

    def get_insights(
        self, 
        category: FeedbackCategory | None = None,
        min_confidence: float = 0.6,
    ) -> list[dict[str, Any]]:
        """
        Get insights derived from feedback and performance data.
        
        Args:
            category: Optional category to filter insights by
            min_confidence: Minimum confidence level for insights
            
        Returns:
            List of insight dictionaries
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("FeedbackMixin must be used with BaseAgent")
            
        # Initialize feedback manager if needed
        if not hasattr(self, "feedback_manager"):
            self.feedback_manager = FeedbackManager()
            return []
            
        # Get insights from feedback manager
        insights = self.feedback_manager.get_insights(
            category=category,
            min_confidence=min_confidence,
        )
        
        # Add basic performance insights if we have enough data
        if len(self.execution_times) >= 5:
            avg_time = sum(self.execution_times) / len(self.execution_times)
            recent_avg = sum(self.execution_times[-5:]) / 5
            
            if recent_avg < avg_time * 0.8:
                insights.append({
                    "type": "performance_improvement",
                    "description": "Recent task execution times have improved significantly",
                    "confidence": 0.7,
                    "category": "performance",
                })
            elif recent_avg > avg_time * 1.2:
                insights.append({
                    "type": "performance_degradation",
                    "description": "Recent task execution times have degraded significantly",
                    "confidence": 0.7,
                    "category": "performance",
                })
                
        # Add completion rate insights
        if self.tasks_received >= 10:
            completion_rate = self.tasks_completed / self.tasks_received
            if completion_rate < 0.7:
                insights.append({
                    "type": "low_completion_rate",
                    "description": f"Task completion rate is low ({completion_rate:.2f})",
                    "confidence": 0.8,
                    "category": "reliability",
                })
            elif completion_rate > 0.95:
                insights.append({
                    "type": "high_completion_rate",
                    "description": f"Task completion rate is excellent ({completion_rate:.2f})",
                    "confidence": 0.8,
                    "category": "reliability",
                })
                
        return insights

    def get_adjustments(
        self,
        category: FeedbackCategory | None = None,
        min_confidence: float = 0.6,
        applied_only: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get adjustments made based on feedback.
        
        Args:
            category: Optional category to filter adjustments by
            min_confidence: Minimum confidence level for adjustments
            applied_only: Whether to include only applied adjustments
            
        Returns:
            List of adjustment dictionaries
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("FeedbackMixin must be used with BaseAgent")
            
        # Initialize feedback manager if needed
        if not hasattr(self, "feedback_manager"):
            self.feedback_manager = FeedbackManager()
            return []
            
        # Get adjustments from feedback manager
        return self.feedback_manager.get_adjustments(
            category=category,
            min_confidence=min_confidence,
            applied_only=applied_only,
        )

    def send_feedback(
        self,
        recipient_id: str,
        category: FeedbackCategory,
        rating: float,
        description: str,
        improvement_suggestions: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Send feedback to another agent.
        
        Args:
            recipient_id: ID of the recipient agent
            category: Feedback category
            rating: Rating value (0.0 to 1.0)
            description: Description of the feedback
            improvement_suggestions: Optional list of improvement suggestions
            context: Optional context information
            
        Returns:
            The message ID of the feedback
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("FeedbackMixin must be used with BaseAgent")
            
        if not self.message_bus:
            raise ValueError("Message bus is required for agent communication")
            
        # Validate rating
        if not 0 <= rating <= 1:
            raise ValueError("Rating must be between 0.0 and 1.0")
            
        # Create feedback message
        message = self.protocol.create_message(
            sender_id=self.id,
            recipient_id=recipient_id,
            message_type=MessageType.FEEDBACK,
            content={
                "category": category.value,
                "rating": rating,
                "description": description,
                "improvement_suggestions": improvement_suggestions or [],
                "context": context or {},
                "severity": FeedbackSeverity.HIGH.value if rating < 0.3 else
                           FeedbackSeverity.MEDIUM.value if rating < 0.7 else
                           FeedbackSeverity.LOW.value,
            },
        )
        
        # Send the message
        self.message_bus.send_message(message)
        self.logger.info(f"Sent feedback to {recipient_id}")
        
        return message.message_id