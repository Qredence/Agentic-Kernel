#!/usr/bin/env python3
"""
File Analysis and Processing Workflow Example.

This example demonstrates a workflow where the FileSurferAgent analyzes a project's
structure, the CoderAgent generates code transformations, and the TerminalAgent
executes them.
"""

import os
import asyncio
import logging
import json
from typing import Dict, List, Any

from agentic_kernel.agents.file_surfer_agent import FileSurferAgent
from agentic_kernel.agents.coder_agent import CoderAgent
from agentic_kernel.agents.terminal_agent import TerminalAgent
from agentic_kernel.agents.orchestrator_agent import OrchestratorAgent
from agentic_kernel.types import Task, WorkflowStep
from agentic_kernel.ledgers.task_ledger import TaskLedger
from agentic_kernel.ledgers.progress_ledger import ProgressLedger
from agentic_kernel.config.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run the file analysis and processing workflow."""
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    # Initialize agents
    file_surfer = FileSurferAgent(config=config)
    coder = CoderAgent(config=config)
    terminal = TerminalAgent(config=config)
    
    # Initialize ledgers
    task_ledger = TaskLedger(goal="Analyze project structure and upgrade dependencies")
    progress_ledger = ProgressLedger(task_id="file_analysis_processing")
    
    # Initialize orchestrator
    orchestrator = OrchestratorAgent(
        config=config,
        task_ledger=task_ledger,
        progress_ledger=progress_ledger
    )
    
    # Register agents with orchestrator
    orchestrator.register_agent(file_surfer)
    orchestrator.register_agent(coder)
    orchestrator.register_agent(terminal)
    
    # Set the project directory to analyze
    # By default, analyze the current project
    project_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    
    # Define the workflow
    workflow = [
        # Step 1: Analyze project structure
        WorkflowStep(
            task=Task(
                name="analyze_project_structure",
                description="Analyze the project directory structure",
                agent_type="file_surfer",
                parameters={
                    "path": project_dir,
                    "max_depth": 3,
                    "include_patterns": ["*.py", "*.md", "pyproject.toml", "requirements.txt"],
                    "exclude_patterns": ["__pycache__", "*.pyc", ".git", ".venv"]
                }
            ),
            dependencies=[]
        ),
        
        # Step 2: Scan dependencies
        WorkflowStep(
            task=Task(
                name="scan_dependencies",
                description="Scan project dependencies from requirement files",
                agent_type="file_surfer",
                parameters={
                    "path": project_dir,
                    "patterns": ["requirements.txt", "pyproject.toml"],
                    "extract_dependencies": True
                }
            ),
            dependencies=["analyze_project_structure"]
        ),
        
        # Step 3: Analyze imports in the codebase
        WorkflowStep(
            task=Task(
                name="analyze_imports",
                description="Analyze imports used in the Python codebase",
                agent_type="file_surfer",
                parameters={
                    "path": os.path.join(project_dir, "src"),
                    "patterns": ["*.py"],
                    "exclude_patterns": ["__pycache__", "*.pyc"],
                    "analysis_type": "imports"
                }
            ),
            dependencies=["analyze_project_structure"]
        ),
        
        # Step 4: Check for outdated dependencies
        WorkflowStep(
            task=Task(
                name="check_outdated_dependencies",
                description="Check for outdated dependencies that need updating",
                agent_type="terminal",
                parameters={
                    "command": "pip list --outdated --format=json",
                    "working_dir": project_dir,
                    "parse_json": True
                }
            ),
            dependencies=["scan_dependencies"]
        ),
        
        # Step 5: Generate dependency upgrade plan
        WorkflowStep(
            task=Task(
                name="generate_upgrade_plan",
                description="Generate a plan for updating dependencies",
                agent_type="coder",
                parameters={
                    "task": "Create a dependency upgrade plan",
                    "format": "markdown",
                    "include_compatibility_notes": True
                }
            ),
            dependencies=["check_outdated_dependencies", "analyze_imports"]
        ),
        
        # Step 6: Update pyproject.toml
        WorkflowStep(
            task=Task(
                name="update_pyproject",
                description="Update pyproject.toml with new dependency versions",
                agent_type="coder",
                parameters={
                    "file": os.path.join(project_dir, "pyproject.toml"),
                    "task": "Update dependencies to latest compatible versions",
                    "backup": True
                }
            ),
            dependencies=["generate_upgrade_plan"]
        ),
        
        # Step 7: Generate code fixes for breaking changes
        WorkflowStep(
            task=Task(
                name="generate_code_fixes",
                description="Generate fixes for breaking changes in the dependencies",
                agent_type="coder",
                parameters={
                    "task": "Update code for compatibility with new dependency versions",
                    "code_dir": os.path.join(project_dir, "src"),
                    "include_patterns": ["*.py"],
                    "exclude_patterns": ["__pycache__", "*.pyc"],
                    "create_patch_files": True
                }
            ),
            dependencies=["update_pyproject"]
        ),
        
        # Step 8: Apply code fixes
        WorkflowStep(
            task=Task(
                name="apply_code_fixes",
                description="Apply the generated code fixes",
                agent_type="terminal",
                parameters={
                    "command": "patch -p0 < {patch_file}",
                    "working_dir": project_dir,
                    "dynamic_command": True
                }
            ),
            dependencies=["generate_code_fixes"]
        ),
        
        # Step 9: Run tests to verify changes
        WorkflowStep(
            task=Task(
                name="run_tests",
                description="Run tests to verify the changes",
                agent_type="terminal",
                parameters={
                    "command": "pytest -xvs tests/",
                    "working_dir": project_dir,
                    "timeout": 300,
                    "capture_output": True
                }
            ),
            dependencies=["apply_code_fixes"]
        ),
        
        # Step 10: Generate upgrade report
        WorkflowStep(
            task=Task(
                name="generate_report",
                description="Generate a comprehensive report of the upgrade process",
                agent_type="coder",
                parameters={
                    "task": "Create a dependency upgrade report",
                    "format": "markdown",
                    "include_sections": [
                        "summary", "updated_dependencies", "breaking_changes",
                        "fixed_issues", "test_results", "recommendations"
                    ]
                }
            ),
            dependencies=["run_tests"]
        )
    ]
    
    # Execute the workflow
    logger.info("Starting file analysis and dependency upgrade workflow...")
    result = await orchestrator.execute_workflow(workflow)
    
    # Output results
    logger.info("Workflow completed with status: %s", result["status"])
    logger.info("Metrics: %s", json.dumps(result["metrics"], indent=2))
    
    # Save the generated report and other artifacts
    output_dir = os.path.join(os.path.dirname(__file__), "output", "dependency_upgrade")
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the upgrade report
    if "generate_report" in result.get("task_results", {}):
        report_content = result["task_results"]["generate_report"].get("content", "")
        report_path = os.path.join(output_dir, "upgrade_report.md")
        
        with open(report_path, "w") as f:
            f.write(report_content)
        logger.info("Saved upgrade report to: %s", report_path)
    
    # Save the upgrade plan
    if "generate_upgrade_plan" in result.get("task_results", {}):
        plan_content = result["task_results"]["generate_upgrade_plan"].get("content", "")
        plan_path = os.path.join(output_dir, "upgrade_plan.md")
        
        with open(plan_path, "w") as f:
            f.write(plan_content)
        logger.info("Saved upgrade plan to: %s", plan_path)
    
    # Save patch files
    if "generate_code_fixes" in result.get("task_results", {}):
        patch_files = result["task_results"]["generate_code_fixes"].get("patch_files", [])
        
        for i, patch_content in enumerate(patch_files):
            patch_path = os.path.join(output_dir, f"fix_{i+1}.patch")
            
            with open(patch_path, "w") as f:
                f.write(patch_content)
            logger.info("Saved patch file to: %s", patch_path)
    
    # Print execution summary
    print("\n" + "="*80)
    print("FILE ANALYSIS AND UPGRADE WORKFLOW SUMMARY")
    print("="*80)
    print(f"Status: {result['status']}")
    print(f"Time taken: {result['metrics']['execution_time']:.2f} seconds")
    print(f"Tasks completed: {len(result['completed_steps'])}/{len(workflow)}")
    
    if result.get("failed_steps"):
        print(f"Failed tasks: {', '.join(result['failed_steps'])}")
    
    # Print analysis summary if available
    if "analyze_project_structure" in result.get("task_results", {}):
        project_stats = result["task_results"]["analyze_project_structure"].get("stats", {})
        print("\nProject Statistics:")
        print(f"  Python files: {project_stats.get('python_files', 'N/A')}")
        print(f"  Total files: {project_stats.get('total_files', 'N/A')}")
        print(f"  Total size: {project_stats.get('total_size', 'N/A')} bytes")
    
    # Print dependency summary if available
    if "scan_dependencies" in result.get("task_results", {}):
        dependencies = result["task_results"]["scan_dependencies"].get("dependencies", {})
        print("\nDependencies:")
        for dep_name, dep_version in dependencies.items()[:10]:  # Show first 10
            print(f"  {dep_name}: {dep_version}")
        if len(dependencies) > 10:
            print(f"  ... and {len(dependencies) - 10} more")
    
    # Print upgrade summary if available
    if "generate_report" in result.get("task_results", {}):
        upgrade_summary = result["task_results"]["generate_report"].get("summary", "")
        print("\nUpgrade Summary:")
        print(f"  {upgrade_summary}")
    
    print("\nArtifacts saved to:")
    print(f"  {output_dir}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main()) 