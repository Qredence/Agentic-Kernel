"""Conflict resolution mechanism for agent interactions.

This module implements a conflict resolution mechanism for handling disagreements
between agents, providing methods for conflict detection, notification, and resolution.

Key features:
1. Conflict detection and classification
2. Conflict notification and escalation
3. Resolution strategies
4. Conflict tracking and history
5. Resolution verification
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of conflicts that can occur between agents."""
    
    RESOURCE_ALLOCATION = "resource_allocation"
    TASK_PRIORITY = "task_priority"
    CAPABILITY_OVERLAP = "capability_overlap"
    DATA_INCONSISTENCY = "data_inconsistency"
    GOAL_CONFLICT = "goal_conflict"
    COMMUNICATION = "communication"


class ConflictSeverity(Enum):
    """Severity levels for conflicts."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Conflict(BaseModel):
    """Represents a conflict between agents.
    
    Attributes:
        conflict_id: Unique identifier for the conflict
        conflict_type: Type of conflict
        description: Description of the conflict
        parties: Agents involved in the conflict
        severity: Severity level of the conflict
        impact: Impact assessment
        created_at: When the conflict was created
        resolution_deadline: Deadline for resolution
        status: Current status of the conflict
    """
    
    conflict_id: str
    conflict_type: ConflictType
    description: str
    parties: List[str]
    severity: ConflictSeverity
    impact: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolution_deadline: Optional[datetime] = None
    status: str = "open"


class ResolutionStrategy(Enum):
    """Strategies for resolving conflicts."""
    
    CONSENSUS = "consensus"
    MEDIATION = "mediation"
    ARBITRATION = "arbitration"
    NEGOTIATION = "negotiation"
    COMPROMISE = "compromise"
    PRIORITIZATION = "prioritization"


class ConflictResolution(BaseModel):
    """Represents a resolution to a conflict.
    
    Attributes:
        conflict_id: ID of the conflict being resolved
        resolution: The proposed resolution
        rationale: Explanation for the resolution
        required_actions: Actions required from involved parties
        verification_method: How to verify the conflict is resolved
        proposed_by: Agent that proposed the resolution
        proposed_at: When the resolution was proposed
    """
    
    conflict_id: str
    resolution: str
    rationale: str
    required_actions: Dict[str, List[str]]
    verification_method: str
    proposed_by: str
    proposed_at: datetime = Field(default_factory=datetime.utcnow)


class ConflictManager:
    """Manages conflict resolution between agents.
    
    This class provides methods for:
    1. Detecting and tracking conflicts
    2. Notifying involved parties
    3. Managing resolution strategies
    4. Verifying conflict resolution
    """
    
    def __init__(self):
        """Initialize the conflict manager."""
        self.active_conflicts: Dict[str, Conflict] = {}
        self.resolution_history: Dict[str, List[ConflictResolution]] = {}
    
    def detect_conflict(
        self,
        conflict_type: ConflictType,
        description: str,
        parties: List[str],
        severity: ConflictSeverity,
        impact: Dict[str, Any],
        resolution_deadline: Optional[datetime] = None,
    ) -> str:
        """Detect and register a new conflict.
        
        Args:
            conflict_type: Type of conflict
            description: Description of the conflict
            parties: Agents involved in the conflict
            severity: Severity level of the conflict
            impact: Impact assessment
            resolution_deadline: Deadline for resolution
            
        Returns:
            ID of the created conflict
        """
        conflict_id = f"conflict_{datetime.utcnow().timestamp()}"
        
        conflict = Conflict(
            conflict_id=conflict_id,
            conflict_type=conflict_type,
            description=description,
            parties=parties,
            severity=severity,
            impact=impact,
            resolution_deadline=resolution_deadline,
        )
        
        self.active_conflicts[conflict_id] = conflict
        logger.info(f"New conflict detected: {conflict_id} ({conflict_type.value})")
        
        return conflict_id
    
    def get_conflict(self, conflict_id: str) -> Optional[Conflict]:
        """Get information about a conflict.
        
        Args:
            conflict_id: ID of the conflict
            
        Returns:
            Conflict information if found, None otherwise
        """
        return self.active_conflicts.get(conflict_id)
    
    def propose_resolution(
        self,
        conflict_id: str,
        resolution: str,
        rationale: str,
        required_actions: Dict[str, List[str]],
        verification_method: str,
        proposed_by: str,
    ) -> bool:
        """Propose a resolution to a conflict.
        
        Args:
            conflict_id: ID of the conflict
            resolution: The proposed resolution
            rationale: Explanation for the resolution
            required_actions: Actions required from involved parties
            verification_method: How to verify the conflict is resolved
            proposed_by: Agent proposing the resolution
            
        Returns:
            True if the resolution was recorded, False otherwise
        """
        if conflict_id not in self.active_conflicts:
            logger.warning(f"Cannot propose resolution: conflict {conflict_id} not found")
            return False
        
        resolution_obj = ConflictResolution(
            conflict_id=conflict_id,
            resolution=resolution,
            rationale=rationale,
            required_actions=required_actions,
            verification_method=verification_method,
            proposed_by=proposed_by,
        )
        
        if conflict_id not in self.resolution_history:
            self.resolution_history[conflict_id] = []
        
        self.resolution_history[conflict_id].append(resolution_obj)
        logger.info(f"Resolution proposed for conflict {conflict_id} by {proposed_by}")
        
        return True
    
    def get_resolution_history(self, conflict_id: str) -> List[Dict[str, Any]]:
        """Get the resolution history for a conflict.
        
        Args:
            conflict_id: ID of the conflict
            
        Returns:
            List of resolution attempts
        """
        if conflict_id not in self.resolution_history:
            return []
        
        return [
            {
                "resolution": resolution.resolution,
                "rationale": resolution.rationale,
                "required_actions": resolution.required_actions,
                "verification_method": resolution.verification_method,
                "proposed_by": resolution.proposed_by,
                "proposed_at": resolution.proposed_at.isoformat(),
            }
            for resolution in self.resolution_history[conflict_id]
        ]
    
    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        verification_result: bool,
    ) -> bool:
        """Mark a conflict as resolved.
        
        Args:
            conflict_id: ID of the conflict
            resolution: The accepted resolution
            verification_result: Result of verification
            
        Returns:
            True if the conflict was resolved, False otherwise
        """
        if conflict_id not in self.active_conflicts:
            logger.warning(f"Cannot resolve conflict: {conflict_id} not found")
            return False
        
        if not verification_result:
            logger.warning(f"Cannot resolve conflict: verification failed for {conflict_id}")
            return False
        
        conflict = self.active_conflicts[conflict_id]
        conflict.status = "resolved"
        logger.info(f"Conflict {conflict_id} resolved with: {resolution}")
        
        return True
    
    def get_active_conflicts(
        self,
        severity: Optional[ConflictSeverity] = None,
        conflict_type: Optional[ConflictType] = None,
    ) -> List[Dict[str, Any]]:
        """Get a list of active conflicts.
        
        Args:
            severity: Filter by severity level
            conflict_type: Filter by conflict type
            
        Returns:
            List of active conflicts
        """
        conflicts = []
        
        for conflict in self.active_conflicts.values():
            if conflict.status != "open":
                continue
            
            if severity and conflict.severity != severity:
                continue
            
            if conflict_type and conflict.conflict_type != conflict_type:
                continue
            
            conflicts.append({
                "conflict_id": conflict.conflict_id,
                "conflict_type": conflict.conflict_type.value,
                "description": conflict.description,
                "parties": conflict.parties,
                "severity": conflict.severity.value,
                "impact": conflict.impact,
                "created_at": conflict.created_at.isoformat(),
                "resolution_deadline": (
                    conflict.resolution_deadline.isoformat()
                    if conflict.resolution_deadline
                    else None
                ),
            })
        
        return conflicts
    
    def suggest_resolution_strategy(
        self,
        conflict_id: str,
    ) -> Tuple[ResolutionStrategy, str]:
        """Suggest a resolution strategy for a conflict.
        
        Args:
            conflict_id: ID of the conflict
            
        Returns:
            Tuple of (strategy, rationale)
        """
        conflict = self.get_conflict(conflict_id)
        if not conflict:
            return ResolutionStrategy.CONSENSUS, "Default to consensus for unknown conflicts"
        
        # Choose strategy based on conflict type and severity
        if conflict.severity == ConflictSeverity.CRITICAL:
            return ResolutionStrategy.ARBITRATION, "Critical conflicts require authoritative resolution"
        
        if conflict.conflict_type == ConflictType.RESOURCE_ALLOCATION:
            return ResolutionStrategy.PRIORITIZATION, "Resource conflicts are best resolved through prioritization"
        
        if len(conflict.parties) > 2:
            return ResolutionStrategy.MEDIATION, "Multi-party conflicts benefit from mediation"
        
        return ResolutionStrategy.NEGOTIATION, "Direct negotiation is appropriate for simple conflicts" 