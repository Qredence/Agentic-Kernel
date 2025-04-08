#!/usr/bin/env python3
"""
Web Research and Code Generation Workflow Example.

This example demonstrates a workflow where the WebSurferAgent researches a topic
and the CoderAgent generates code based on the research findings.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List

from agentic_kernel.agents.coder_agent import CoderAgent
from agentic_kernel.agents.orchestrator_agent import OrchestratorAgent
from agentic_kernel.agents.web_surfer_agent import WebSurferAgent
from agentic_kernel.config.config_manager import ConfigManager
from agentic_kernel.ledgers.progress_ledger import ProgressLedger
from agentic_kernel.ledgers.task_ledger import TaskLedger
from agentic_kernel.types import Task, WorkflowStep

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run the web research and code generation workflow."""
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    # Initialize agents
    web_surfer = WebSurferAgent(config=config)
    coder = CoderAgent(config=config)
    
    # Initialize ledgers
    task_ledger = TaskLedger(goal="Research and generate code for asynchronous programming patterns")
    progress_ledger = ProgressLedger(task_id="web_research_code_generation")
    
    # Initialize orchestrator
    orchestrator = OrchestratorAgent(
        config=config,
        task_ledger=task_ledger,
        progress_ledger=progress_ledger
    )
    
    # Register agents with orchestrator
    orchestrator.register_agent(web_surfer)
    orchestrator.register_agent(coder)
    
    # Define the workflow
    workflow = [
        # Step 1: Research asynchronous programming patterns
        WorkflowStep(
            task=Task(
                name="research_async_patterns",
                description="Research modern asynchronous programming patterns in Python",
                agent_type="web_surfer",
                parameters={
                    "query": "Python asyncio best practices 2023",
                    "num_results": 3,
                    "detailed": True
                }
            ),
            dependencies=[]
        ),
        
        # Step 2: Research error handling in async code
        WorkflowStep(
            task=Task(
                name="research_error_handling",
                description="Research error handling patterns in asynchronous Python code",
                agent_type="web_surfer",
                parameters={
                    "query": "Python asyncio error handling patterns",
                    "num_results": 2,
                    "detailed": True
                }
            ),
            dependencies=[]
        ),
        
        # Step 3: Generate utility functions based on research
        WorkflowStep(
            task=Task(
                name="generate_async_utilities",
                description="Generate async utility functions based on research findings",
                agent_type="coder",
                parameters={
                    "language": "python",
                    "task": "Create a set of async utility functions for common patterns",
                    "dependencies": ["asyncio", "contextlib"],
                    "include_docstrings": True,
                    "include_tests": True
                }
            ),
            dependencies=["research_async_patterns", "research_error_handling"]
        ),
        
        # Step 4: Generate error handling examples
        WorkflowStep(
            task=Task(
                name="generate_error_handling_examples",
                description="Generate example code showing async error handling patterns",
                agent_type="coder",
                parameters={
                    "language": "python",
                    "task": "Create examples of error handling in async code",
                    "dependencies": ["asyncio"],
                    "include_comments": True
                }
            ),
            dependencies=["research_error_handling"]
        ),
        
        # Step 5: Create a comprehensive async module
        WorkflowStep(
            task=Task(
                name="create_async_module",
                description="Create a comprehensive async module combining utilities and error handling",
                agent_type="coder",
                parameters={
                    "language": "python",
                    "task": "Create a complete async module with utilities and error handling",
                    "dependencies": ["asyncio", "contextlib", "typing"],
                    "include_docstrings": True,
                    "include_examples": True,
                    "structure": {
                        "module_name": "async_toolbox",
                        "submodules": ["utils", "error_handling", "patterns"]
                    }
                }
            ),
            dependencies=["generate_async_utilities", "generate_error_handling_examples"]
        )
    ]
    
    # Execute the workflow
    logger.info("Starting web research and code generation workflow...")
    result = await orchestrator.execute_workflow(workflow)
    
    # Output results
    logger.info("Workflow completed with status: %s", result["status"])
    logger.info("Metrics: %s", json.dumps(result["metrics"], indent=2))
    
    # Save generated code files
    output_dir = os.path.join(os.path.dirname(__file__), "output", "async_toolbox")
    os.makedirs(output_dir, exist_ok=True)
    
    for task_name, task_result in result.get("task_results", {}).items():
        if task_name.startswith("generate_") or task_name == "create_async_module":
            files = task_result.get("files", [])
            for file_info in files:
                file_path = os.path.join(output_dir, file_info["name"])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, "w") as f:
                    f.write(file_info["content"])
                logger.info("Saved file: %s", file_path)
    
    logger.info("All generated files saved to: %s", output_dir)
    
    # Print summary of findings
    print("\n" + "="*80)
    print("WORKFLOW EXECUTION SUMMARY")
    print("="*80)
    print(f"Status: {result['status']}")
    print(f"Time taken: {result['metrics']['execution_time']:.2f} seconds")
    print(f"Tasks completed: {len(result['completed_steps'])}/{len(workflow)}")
    
    if result.get("failed_steps"):
        print(f"Failed tasks: {', '.join(result['failed_steps'])}")
    
    print("\nGenerated files:")
    for task_name, task_result in result.get("task_results", {}).items():
        if task_name.startswith("generate_") or task_name == "create_async_module":
            files = task_result.get("files", [])
            for file_info in files:
                print(f"  - {file_info['name']}")
    
    print("\nResearch findings summary:")
    for task_name, task_result in result.get("task_results", {}).items():
        if task_name.startswith("research_"):
            summary = task_result.get("summary", "No summary available")
            print(f"\n{task_name}:")
            print(f"  {summary}")
    
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main()) 