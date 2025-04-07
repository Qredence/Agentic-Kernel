#!/usr/bin/env python3
"""Test script for core components of the Agentic Kernel architecture.

This script tests imports and initialization of core components and writes
results to a log file for later inspection.
"""

import os
import sys
import uuid
import logging
import traceback
from datetime import datetime
from pathlib import Path

# Ensure PYTHONPATH includes the project root
current_dir = Path(__file__).resolve().parent
project_root = current_dir
sys.path.insert(0, str(project_root))

# Set up logging to file
log_file = project_root / "debug_log.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("debug_test")

def log_section(title):
    """Log a section separator with title."""
    border = "=" * 80
    logger.info(border)
    logger.info(f"= {title.center(76)} =")
    logger.info(border)

def test_imports():
    """Test importing all critical modules."""
    log_section("Testing Imports")
    
    modules = [
        ("agentic_kernel.config.loader", "ConfigLoader"),
        ("agentic_kernel.config", "AgentConfig"),
        ("agentic_kernel.agents.base", "BaseAgent"),
        ("agentic_kernel.types", ["Task", "WorkflowStep"]),
        ("agentic_kernel.ledgers", ["TaskLedger", "ProgressLedger"]),
        ("agentic_kernel.orchestrator", "OrchestratorAgent"),
    ]
    
    success = True
    
    for module_path, classes in modules:
        try:
            logger.info(f"Importing {module_path}...")
            module = __import__(module_path, fromlist=["*"])
            
            if isinstance(classes, list):
                for cls_name in classes:
                    cls = getattr(module, cls_name)
                    logger.info(f"  ✅ Successfully imported {cls_name} from {module_path}")
            else:
                cls = getattr(module, classes)
                logger.info(f"  ✅ Successfully imported {classes} from {module_path}")
                
        except ImportError as e:
            logger.error(f"  ❌ Failed to import {module_path}: {e}")
            success = False
        except AttributeError as e:
            logger.error(f"  ❌ Failed to find {classes} in {module_path}: {e}")
            success = False
        except Exception as e:
            logger.error(f"  ❌ Unexpected error importing {module_path}: {e}")
            traceback.print_exc()
            success = False
    
    return success

def test_initialization():
    """Test initializing core components."""
    log_section("Testing Component Initialization")
    
    success = True
    
    try:
        # Import required components
        from agentic_kernel.config.loader import ConfigLoader
        from agentic_kernel.ledgers import TaskLedger, ProgressLedger
        
        # Initialize ConfigLoader
        logger.info("Initializing ConfigLoader...")
        config_loader = ConfigLoader()
        logger.info("  ✅ ConfigLoader initialized successfully")
        
        # Initialize TaskLedger
        logger.info("Initializing TaskLedger...")
        task_ledger = TaskLedger(goal="Test goal for debugging")
        logger.info("  ✅ TaskLedger initialized successfully")
        logger.info(f"    task_id: {task_ledger.task_id}")
        logger.info(f"    goal: {task_ledger.goal}")
        
        # Initialize ProgressLedger
        logger.info("Initializing ProgressLedger...")
        progress_ledger = ProgressLedger(task_id=str(uuid.uuid4()))
        logger.info("  ✅ ProgressLedger initialized successfully")
        logger.info(f"    task_id: {progress_ledger.task_id}")
        
    except Exception as e:
        logger.error(f"  ❌ Component initialization failed: {e}")
        traceback.print_exc()
        success = False
    
    return success

def main():
    """Run all tests."""
    log_section("Testing Core Components")
    logger.info(f"Starting tests at {datetime.now()}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"Project root: {project_root}")
    
    # Test imports
    imports_ok = test_imports()
    if not imports_ok:
        logger.error("Import tests failed. Stopping further tests.")
        return False
    
    # Test initialization
    init_ok = test_initialization()
    if not init_ok:
        logger.error("Initialization tests failed.")
        return False
    
    logger.info("All tests passed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    
    logger.info(f"\nTest results written to {log_file}")
    print(f"\nTest results written to {log_file}")
    
    sys.exit(0 if success else 1) 