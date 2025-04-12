"""Shared test fixtures."""

import pytest
from agentic_kernel.communication.coordination import CoordinationManager
from agentic_kernel.communication.trust import TrustManager
from ..agents.task_manager import TaskManagerAgent
from ..agents.worker import WorkerAgent
from ..agents.validator import ValidatorAgent

@pytest.fixture(scope="session")
def coordination_manager():
    """Provide a shared CoordinationManager instance."""
    return CoordinationManager()

@pytest.fixture(scope="session")
def trust_manager():
    """Provide a shared TrustManager instance."""
    return TrustManager()

@pytest.fixture
def task_manager(coordination_manager):
    """Create a TaskManagerAgent instance with shared CoordinationManager."""
    return TaskManagerAgent(coordination_manager=coordination_manager)

@pytest.fixture
def worker(coordination_manager):
    """Create a WorkerAgent instance with shared CoordinationManager."""
    return WorkerAgent(coordination_manager=coordination_manager)

@pytest.fixture
def validator(coordination_manager, trust_manager):
    """Create a ValidatorAgent instance with shared managers."""
    return ValidatorAgent(coordination_manager=coordination_manager, trust_manager=trust_manager) 