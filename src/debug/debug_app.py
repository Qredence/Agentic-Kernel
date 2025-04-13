"""Debug script to validate imports and initialization of key components."""

import os
import logging
import sys
from dotenv import load_dotenv
from typing import Dict, Any
from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.plugins.base import BasePlugin
from agentic_kernel.orchestrator.core import OrchestratorAgent
from agentic_kernel.config.loader import ConfigLoader
from agentic_kernel.config_types import AgentConfig
from agentic_kernel.ledgers import TaskLedger, ProgressLedger
from agentic_kernel.types import Task, WorkflowStep

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def main():
    """Main debug function to validate components."""
    logger.info("Starting debug validation")

    try:
        # Test imports
        logger.info("Testing imports...")
        from agentic_kernel.config.loader import ConfigLoader
        from agentic_kernel.config import AgentConfig
        from agentic_kernel.agents.base import BaseAgent
        from agentic_kernel.types import Task, WorkflowStep
        from agentic_kernel.ledgers import TaskLedger, ProgressLedger
        from agentic_kernel.orchestrator.core import OrchestratorAgent

        logger.info("Imports successful")

        # Test initialization
        logger.info("Testing component initialization...")
        config_loader = ConfigLoader()
        task_ledger = TaskLedger(goal="Test goal")
        progress_ledger = ProgressLedger(task_id="test_task_id")

        logger.info("Component initialization successful")

        return 0
    except Exception as e:
        logger.error(f"Debug validation failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
