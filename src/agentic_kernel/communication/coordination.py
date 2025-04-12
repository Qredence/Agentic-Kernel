"""Coordination protocol for synchronizing agent activities.

This module implements a coordination protocol for synchronizing activities
between agents, providing methods for activity planning, scheduling, and
execution coordination.

Key features:
1. Activity planning and scheduling
2. Dependency management
3. Resource coordination
4. Timeline synchronization
5. Progress tracking
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ActivityStatus(Enum):
    """Status of an activity in the coordination process."""
    
    PLANNED = "planned"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class ActivityPriority(Enum):
    """Priority levels for activities."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Activity(BaseModel):
    """Represents an activity in the coordination process.
    
    Attributes:
        activity_id: Unique identifier for the activity
        name: Name of the activity
        description: Description of the activity
        agent_id: ID of the agent responsible for the activity
        dependencies: IDs of activities this activity depends on
        required_resources: Resources required for the activity
        estimated_duration: Estimated duration in seconds
        priority: Priority level of the activity
        status: Current status of the activity
        created_at: When the activity was created
        scheduled_start: When the activity is scheduled to start
        actual_start: When the activity actually started
        completed_at: When the activity was completed
    """
    
    activity_id: str
    name: str
    description: str
    agent_id: str
    dependencies: List[str] = Field(default_factory=list)
    required_resources: Dict[str, Any] = Field(default_factory=dict)
    estimated_duration: float
    priority: ActivityPriority
    status: ActivityStatus = ActivityStatus.PLANNED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_start: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ResourceAllocation(BaseModel):
    """Represents a resource allocation for an activity.
    
    Attributes:
        resource_id: ID of the resource
        activity_id: ID of the activity
        start_time: When the allocation starts
        end_time: When the allocation ends
        status: Current status of the allocation
    """
    
    resource_id: str
    activity_id: str
    start_time: datetime
    end_time: datetime
    status: str = "reserved"


class CoordinationManager:
    """Manages coordination between agent activities.
    
    This class provides methods for:
    1. Planning and scheduling activities
    2. Managing dependencies
    3. Allocating resources
    4. Tracking progress
    5. Synchronizing timelines
    """
    
    def __init__(self):
        """Initialize the coordination manager."""
        self.activities: Dict[str, Activity] = {}
        self.resource_allocations: Dict[str, List[ResourceAllocation]] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
    
    def create_activity(
        self,
        name: str,
        description: str,
        agent_id: str,
        estimated_duration: float,
        priority: ActivityPriority,
        dependencies: Optional[List[str]] = None,
        required_resources: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new activity.
        
        Args:
            name: Name of the activity
            description: Description of the activity
            agent_id: ID of the agent responsible
            estimated_duration: Estimated duration in seconds
            priority: Priority level of the activity
            dependencies: IDs of activities this activity depends on
            required_resources: Resources required for the activity
            
        Returns:
            ID of the created activity
        """
        activity_id = f"activity_{datetime.utcnow().timestamp()}"
        
        activity = Activity(
            activity_id=activity_id,
            name=name,
            description=description,
            agent_id=agent_id,
            dependencies=dependencies or [],
            required_resources=required_resources or {},
            estimated_duration=estimated_duration,
            priority=priority,
        )
        
        self.activities[activity_id] = activity
        self.dependency_graph[activity_id] = set(dependencies or [])
        
        logger.info(f"Created new activity: {activity_id} ({name})")
        return activity_id
    
    def schedule_activity(
        self,
        activity_id: str,
        start_time: datetime,
    ) -> bool:
        """Schedule an activity to start at a specific time.
        
        Args:
            activity_id: ID of the activity
            start_time: When the activity should start
            
        Returns:
            True if the activity was scheduled, False otherwise
        """
        if activity_id not in self.activities:
            logger.warning(f"Cannot schedule activity: {activity_id} not found")
            return False
        
        activity = self.activities[activity_id]
        
        # Check if dependencies are completed
        for dep_id in activity.dependencies:
            if dep_id not in self.activities:
                logger.warning(f"Cannot schedule activity: dependency {dep_id} not found")
                return False
            
            dep = self.activities[dep_id]
            if dep.status != ActivityStatus.COMPLETED:
                logger.warning(f"Cannot schedule activity: dependency {dep_id} not completed")
                return False
        
        # Check resource availability
        if not self._check_resource_availability(activity_id, start_time):
            logger.warning(f"Cannot schedule activity: resources not available")
            return False
        
        # Schedule the activity
        activity.scheduled_start = start_time
        activity.status = ActivityStatus.SCHEDULED
        
        # Allocate resources
        self._allocate_resources(activity_id, start_time)
        
        logger.info(f"Scheduled activity {activity_id} to start at {start_time}")
        return True
    
    def start_activity(self, activity_id: str) -> bool:
        """Mark an activity as started.
        
        Args:
            activity_id: ID of the activity
            
        Returns:
            True if the activity was started, False otherwise
        """
        if activity_id not in self.activities:
            logger.warning(f"Cannot start activity: {activity_id} not found")
            return False
        
        activity = self.activities[activity_id]
        
        if activity.status != ActivityStatus.SCHEDULED:
            logger.warning(f"Cannot start activity: not scheduled")
            return False
        
        activity.status = ActivityStatus.IN_PROGRESS
        activity.actual_start = datetime.utcnow()
        
        logger.info(f"Started activity {activity_id}")
        return True
    
    def complete_activity(self, activity_id: str) -> bool:
        """Mark an activity as completed.
        
        Args:
            activity_id: ID of the activity
            
        Returns:
            True if the activity was completed, False otherwise
        """
        if activity_id not in self.activities:
            logger.warning(f"Cannot complete activity: {activity_id} not found")
            return False
        
        activity = self.activities[activity_id]
        
        if activity.status != ActivityStatus.IN_PROGRESS:
            logger.warning(f"Cannot complete activity: not in progress")
            return False
        
        activity.status = ActivityStatus.COMPLETED
        activity.completed_at = datetime.utcnow()
        
        # Release resources
        self._release_resources(activity_id)
        
        logger.info(f"Completed activity {activity_id}")
        return True
    
    def get_activity_status(self, activity_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of an activity.
        
        Args:
            activity_id: ID of the activity
            
        Returns:
            Activity status information if found, None otherwise
        """
        if activity_id not in self.activities:
            return None
        
        activity = self.activities[activity_id]
        
        return {
            "activity_id": activity.activity_id,
            "name": activity.name,
            "status": activity.status.value,
            "agent_id": activity.agent_id,
            "scheduled_start": (
                activity.scheduled_start.isoformat()
                if activity.scheduled_start
                else None
            ),
            "actual_start": (
                activity.actual_start.isoformat()
                if activity.actual_start
                else None
            ),
            "completed_at": (
                activity.completed_at.isoformat()
                if activity.completed_at
                else None
            ),
            "dependencies": activity.dependencies,
            "required_resources": activity.required_resources,
        }
    
    def get_blocked_activities(self) -> List[Dict[str, Any]]:
        """Get a list of activities that are blocked.
        
        Returns:
            List of blocked activities
        """
        blocked = []
        
        for activity in self.activities.values():
            if activity.status == ActivityStatus.BLOCKED:
                blocked.append({
                    "activity_id": activity.activity_id,
                    "name": activity.name,
                    "agent_id": activity.agent_id,
                    "blocking_dependencies": [
                        dep_id
                        for dep_id in activity.dependencies
                        if dep_id in self.activities
                        and self.activities[dep_id].status != ActivityStatus.COMPLETED
                    ],
                })
        
        return blocked
    
    def _check_resource_availability(
        self,
        activity_id: str,
        start_time: datetime,
    ) -> bool:
        """Check if required resources are available.
        
        Args:
            activity_id: ID of the activity
            start_time: When the activity would start
            
        Returns:
            True if resources are available, False otherwise
        """
        activity = self.activities[activity_id]
        end_time = start_time + timedelta(seconds=activity.estimated_duration)
        
        for resource_id, requirements in activity.required_resources.items():
            if resource_id not in self.resource_allocations:
                continue
            
            for allocation in self.resource_allocations[resource_id]:
                if (
                    start_time < allocation.end_time
                    and end_time > allocation.start_time
                ):
                    return False
        
        return True
    
    def _allocate_resources(
        self,
        activity_id: str,
        start_time: datetime,
    ) -> None:
        """Allocate resources for an activity.
        
        Args:
            activity_id: ID of the activity
            start_time: When the activity starts
        """
        activity = self.activities[activity_id]
        end_time = start_time + timedelta(seconds=activity.estimated_duration)
        
        for resource_id, requirements in activity.required_resources.items():
            allocation = ResourceAllocation(
                resource_id=resource_id,
                activity_id=activity_id,
                start_time=start_time,
                end_time=end_time,
            )
            
            if resource_id not in self.resource_allocations:
                self.resource_allocations[resource_id] = []
            
            self.resource_allocations[resource_id].append(allocation)
    
    def _release_resources(self, activity_id: str) -> None:
        """Release resources allocated to an activity.
        
        Args:
            activity_id: ID of the activity
        """
        for allocations in self.resource_allocations.values():
            for allocation in allocations[:]:
                if allocation.activity_id == activity_id:
                    allocations.remove(allocation)
    
    def get_activity_timeline(
        self,
        agent_id: Optional[str] = None,
        priority: Optional[ActivityPriority] = None,
    ) -> List[Dict[str, Any]]:
        """Get a timeline of activities.
        
        Args:
            agent_id: Filter by agent ID
            priority: Filter by priority level
            
        Returns:
            List of activities in timeline order
        """
        timeline = []
        
        for activity in self.activities.values():
            if agent_id and activity.agent_id != agent_id:
                continue
            
            if priority and activity.priority != priority:
                continue
            
            if not activity.scheduled_start:
                continue
            
            timeline.append({
                "activity_id": activity.activity_id,
                "name": activity.name,
                "agent_id": activity.agent_id,
                "priority": activity.priority.value,
                "status": activity.status.value,
                "scheduled_start": activity.scheduled_start.isoformat(),
                "estimated_duration": activity.estimated_duration,
                "dependencies": activity.dependencies,
            })
        
        timeline.sort(key=lambda x: x["scheduled_start"])
        return timeline 