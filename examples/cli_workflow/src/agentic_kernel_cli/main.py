"""CLI application demonstrating Agentic Kernel's workflow orchestration capabilities."""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

import typer
from agentic_kernel.agents import (
    CoderAgent,
    FileSurferAgent,
    OrchestratorAgent,
    TerminalAgent,
    WebSurferAgent,
)
from agentic_kernel.config import ConfigLoader
from agentic_kernel.ledgers import ProgressLedger, TaskLedger
from rich.console import Console
from rich.logging import RichHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("cli")
console = Console()

app = typer.Typer(help="Agentic Kernel CLI Workflow Demo")

@app.command()
def execute_workflow(
    task: str = typer.Argument(..., help="The task to execute"),
    working_dir: Optional[Path] = typer.Option(
        None,
        "--working-dir",
        "-d",
        help="Working directory for file operations"
    ),
    agents: Optional[List[str]] = typer.Option(
        None,
        "--agents",
        "-a",
        help="Specific agents to use (default: all)"
    ),
):
    """Execute a workflow with the specified task."""
    try:
        # Load configuration
        config = ConfigLoader()

        # Initialize ledgers
        task_ledger = TaskLedger()
        progress_ledger = ProgressLedger()

        # Create agents
        available_agents = {
            "web": WebSurferAgent(config=config.get_agent_config("web_surfer")),
            "file": FileSurferAgent(config=config.get_agent_config("file_surfer")),
            "code": CoderAgent(config=config.get_agent_config("coder")),
            "terminal": TerminalAgent(config=config.get_agent_config("terminal")),
        }

        # Filter agents if specified
        if agents:
            selected_agents = {
                name: agent for name, agent in available_agents.items()
                if name in agents
            }
        else:
            selected_agents = available_agents

        # Create orchestrator
        orchestrator = OrchestratorAgent(
            config=config.get_agent_config("orchestrator"),
            agents=list(selected_agents.values()),
            task_ledger=task_ledger,
            progress_ledger=progress_ledger,
        )

        # Execute workflow
        asyncio.run(_run_workflow(
            orchestrator=orchestrator,
            task=task,
            working_dir=working_dir,
        ))

    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}", exc_info=True)
        raise typer.Exit(1)

async def _run_workflow(
    orchestrator: OrchestratorAgent,
    task: str,
    working_dir: Optional[Path] = None,
) -> None:
    """Run the workflow asynchronously."""
    try:
        # Set working directory if provided
        if working_dir:
            working_dir = working_dir.resolve()
            logger.info(f"Setting working directory to: {working_dir}")
            await orchestrator.set_working_directory(working_dir)

        # Execute the workflow
        with console.status("[bold green]Executing workflow...") as status:
            result = await orchestrator.execute_workflow(task)

            # Display results
            console.print("\n[bold]Workflow Results:[/bold]")
            console.print(f"Task: {task}")
            console.print(f"Status: {result.status}")
            console.print("\nSteps Executed:")
            for step in result.steps:
                console.print(f"- {step.name}: {step.status}")

            if result.output:
                console.print("\nOutput:")
                console.print(result.output)

            # Display metrics
            console.print("\n[bold]Metrics:[/bold]")
            metrics = orchestrator.get_metrics()
            for key, value in metrics.items():
                console.print(f"{key}: {value}")

    except Exception as e:
        logger.error(f"Error in workflow execution: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    app()
