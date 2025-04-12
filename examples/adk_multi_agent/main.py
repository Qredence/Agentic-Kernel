"""Main example demonstrating the ADK multi-agent system."""

import asyncio
import logging
from datetime import datetime, timedelta

from agentic_kernel.communication.coordination import CoordinationManager
from agentic_kernel.communication.trust import TrustManager

from .agents.task_manager import TaskManagerAgent
from .agents.validator import ValidatorAgent
from .agents.worker import WorkerAgent
from .utils.base_agent import InMemorySessionService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Main function to run the multi-agent system."""
    # Initialize session service
    session_service = InMemorySessionService()
    
    # Initialize shared managers
    coordination_manager = CoordinationManager()
    trust_manager = TrustManager()
    
    # Create agents with shared managers
    task_manager = TaskManagerAgent(coordination_manager=coordination_manager)
    worker = WorkerAgent(coordination_manager=coordination_manager)
    validator = ValidatorAgent(coordination_manager=coordination_manager, trust_manager=trust_manager)
    
    # Create a session
    session = session_service.create_session(
        state={},
        app_name="multi_agent_system",
        user_id="user1",
    )
    
    # Example task
    task_description = "Process and analyze customer feedback data"
    logger.info(f"--- Starting task: '{task_description}' ---")
    
    # Task Manager creates and assigns task
    logger.info("Task Manager: Creating and scheduling task...")
    task_result = await task_manager.create_task(
        task_description=task_description,
        priority="high",
        deadline=(datetime.utcnow() + timedelta(hours=1)).isoformat(),
    )
    # Check if task was created and scheduled successfully (based on TaskManagerAgent changes)
    if not task_result or task_result.get("status") != "scheduled":
        logger.error(f"Task Manager: Failed to create/schedule task. Result: {task_result}")
        return # Stop execution if task creation failed
    logger.info(f"Task Manager: Task {task_result['activity_id']} created and scheduled.")
    
    # Worker executes task
    logger.info(f"Worker Agent: Executing task {task_result['activity_id']}...")
    execution_result = await worker.execute_task(task_result["activity_id"])
    logger.info(f"Worker Agent: Task execution result: {execution_result}")
    
    # Validator validates result
    logger.info(f"Validator Agent: Validating task {task_result['activity_id']}...")
    validation_result = await validator.validate_task(task_result["activity_id"])
    logger.info(f"Validator Agent: Task validation result: {validation_result}")
    
    # Update trust metrics based on validation
    validation_successful = validation_result["status"] == "valid"
    logger.info(f"Validator Agent: Updating trust for worker based on validation ({'Success' if validation_successful else 'Failure'})...")
    trust_update = await validator.update_trust(
        agent_id="worker", # Assuming worker agent's name/ID is 'worker'
        success=validation_successful,
    )
    logger.info(f"Validator Agent: Trust update result: {trust_update}")
    
    logger.info("--- Task finished --- ")

if __name__ == "__main__":
    asyncio.run(main()) 