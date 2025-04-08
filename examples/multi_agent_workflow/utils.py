#!/usr/bin/env python3
"""
Utilities for the multi-agent workflow examples.

This module provides helper functions for workflow visualization, 
analysis, and reporting.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

# Try to import visualization libraries, but don't fail if they're not available
try:
    import networkx as nx
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    HAS_VISUALIZATION = True
except ImportError:
    HAS_VISUALIZATION = False

logger = logging.getLogger(__name__)


def visualize_workflow(result: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generate a visualization of workflow execution.
    
    Args:
        result: The workflow execution result
        output_path: Optional path to save the visualization image
        
    Returns:
        Path to the saved visualization or message if visualization failed
    """
    if not HAS_VISUALIZATION:
        message = (
            "Visualization libraries not available. "
            "Please install optional dependencies: pip install networkx matplotlib"
        )
        logger.warning(message)
        return message
    
    # Create a directed graph
    G = nx.DiGraph()
    
    # Extract workflow data
    task_results = result.get("task_results", {})
    completed_steps = set(result.get("completed_steps", []))
    failed_steps = set(result.get("failed_steps", []))
    retried_steps = set(result.get("retried_steps", []))
    
    # Add nodes (tasks)
    for task_name, task_data in task_results.items():
        # Determine node color based on task status
        if task_name in failed_steps:
            color = 'red'
            status = 'failed'
        elif task_name in retried_steps:
            color = 'orange'
            status = 'retried'
        elif task_name in completed_steps:
            color = 'green'
            status = 'completed'
        else:
            color = 'gray'
            status = 'unknown'
        
        # Extract metadata
        agent_type = task_data.get("agent_type", "unknown")
        start_time = task_data.get("start_time", 0)
        end_time = task_data.get("end_time", 0)
        duration = end_time - start_time if end_time and start_time else 0
        
        # Add node with attributes
        G.add_node(
            task_name,
            color=color,
            status=status,
            agent_type=agent_type,
            duration=duration,
            start_time=start_time,
            end_time=end_time
        )
    
    # Add edges (dependencies)
    for task_name, task_data in task_results.items():
        dependencies = task_data.get("dependencies", [])
        for dep in dependencies:
            if dep in task_results:
                G.add_edge(dep, task_name)
    
    # Create the plot
    plt.figure(figsize=(14, 10))
    
    # Define node colors based on status
    node_colors = [G.nodes[n]['color'] for n in G.nodes]
    
    # Use positions that show workflow dependencies clearly
    pos = nx.nx_agraph.graphviz_layout(G, prog='dot') if hasattr(nx, 'nx_agraph') else nx.spring_layout(G)
    
    # Draw the graph
    nx.draw(
        G,
        pos=pos,
        with_labels=True,
        node_color=node_colors,
        node_size=2500,
        font_size=8,
        font_weight='bold',
        arrows=True,
        arrowsize=15,
        width=2
    )
    
    # Add a title with summary information
    success_rate = result.get("metrics", {}).get("success_rate", 0) * 100
    execution_time = result.get("metrics", {}).get("execution_time", 0)
    num_completed = len(completed_steps)
    num_failed = len(failed_steps)
    
    plt.title(
        f"Workflow Execution: {success_rate:.1f}% Success Rate\n"
        f"Completed: {num_completed}, Failed: {num_failed}, Time: {execution_time:.2f}s",
        fontsize=12
    )
    
    # Determine the output path
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.path.dirname(__file__), "output", "visualizations")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"workflow_viz_{timestamp}.png")
    
    # Save the visualization
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    
    logger.info("Saved workflow visualization to: %s", output_path)
    return output_path


def generate_workflow_report(result: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generate a comprehensive report of workflow execution.
    
    Args:
        result: The workflow execution result
        output_path: Optional path to save the report
        
    Returns:
        Path to the saved report
    """
    # Extract workflow data
    task_results = result.get("task_results", {})
    completed_steps = set(result.get("completed_steps", []))
    failed_steps = set(result.get("failed_steps", []))
    retried_steps = set(result.get("retried_steps", []))
    metrics = result.get("metrics", {})
    
    # Generate report content
    report = []
    
    # Add header
    report.append("# Workflow Execution Report")
    report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Add summary section
    report.append("## Summary")
    report.append(f"Status: {result.get('status', 'Unknown')}")
    report.append(f"Success Rate: {metrics.get('success_rate', 0) * 100:.1f}%")
    report.append(f"Execution Time: {metrics.get('execution_time', 0):.2f} seconds")
    report.append(f"Tasks Completed: {len(completed_steps)}")
    report.append(f"Tasks Failed: {len(failed_steps)}")
    report.append(f"Tasks Retried: {len(retried_steps)}\n")
    
    # Add per-agent performance
    agent_stats = metrics.get("agent_stats", {})
    if agent_stats:
        report.append("## Agent Performance")
        report.append("| Agent Type | Tasks | Success Rate | Avg Duration (s) |")
        report.append("|------------|-------|--------------|-----------------|")
        
        for agent, stats in agent_stats.items():
            tasks = stats.get("tasks", 0)
            success_rate = stats.get("success_rate", 0) * 100
            avg_duration = stats.get("avg_duration", 0)
            report.append(f"| {agent} | {tasks} | {success_rate:.1f}% | {avg_duration:.2f} |")
        report.append("")
    
    # Add task details
    report.append("## Task Details")
    
    for task_name, task_data in sorted(task_results.items()):
        status = "Completed"
        if task_name in failed_steps:
            status = "Failed"
        elif task_name in retried_steps:
            status = "Retried"
            
        agent_type = task_data.get("agent_type", "unknown")
        start_time = task_data.get("start_time", 0)
        end_time = task_data.get("end_time", 0)
        duration = end_time - start_time if end_time and start_time else 0
        
        report.append(f"### {task_name}")
        report.append(f"Status: {status}")
        report.append(f"Agent: {agent_type}")
        report.append(f"Duration: {duration:.2f} seconds")
        
        if task_data.get("parameters"):
            report.append("Parameters:")
            for param, value in task_data["parameters"].items():
                # Truncate long parameter values
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                report.append(f"- {param}: {value}")
        
        if task_data.get("dependencies"):
            report.append("Dependencies:")
            for dep in task_data["dependencies"]:
                report.append(f"- {dep}")
        
        if task_data.get("output"):
            output = task_data["output"]
            # Truncate long outputs
            if isinstance(output, str) and len(output) > 200:
                output = output[:200] + "..."
            report.append("Output:")
            report.append(f"```\n{output}\n```")
        
        if task_name in failed_steps and task_data.get("error"):
            report.append("Error:")
            report.append(f"```\n{task_data['error']}\n```")
            
        report.append("")  # Add empty line between tasks
    
    # Add workflow visualization
    if HAS_VISUALIZATION:
        report.append("## Workflow Visualization")
        # We'll generate a visualization and reference it
        viz_path = visualize_workflow(result)
        report.append(f"![Workflow Visualization]({os.path.basename(viz_path)})")
    
    # Determine the output path
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.path.dirname(__file__), "output", "reports")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"workflow_report_{timestamp}.md")
    
    # Write the report
    with open(output_path, "w") as f:
        f.write("\n".join(report))
    
    logger.info("Saved workflow report to: %s", output_path)
    return output_path


def save_workflow_result(result: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Save the raw workflow execution result to a JSON file.
    
    Args:
        result: The workflow execution result
        output_path: Optional path to save the result
        
    Returns:
        Path to the saved result
    """
    # Clone the result to avoid modifying the original
    result_copy = json.loads(json.dumps(result))
    
    # Remove potentially large or non-serializable data
    for task_name, task_data in result_copy.get("task_results", {}).items():
        if "output" in task_data and isinstance(task_data["output"], str) and len(task_data["output"]) > 1000:
            task_data["output"] = task_data["output"][:1000] + "... [truncated]"
    
    # Determine the output path
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.path.dirname(__file__), "output", "results")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"workflow_result_{timestamp}.json")
    
    # Write the result
    with open(output_path, "w") as f:
        json.dump(result_copy, f, indent=2)
    
    logger.info("Saved workflow result to: %s", output_path)
    return output_path


def analyze_workflow_performance(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze workflow performance and identify bottlenecks.
    
    Args:
        result: The workflow execution result
        
    Returns:
        Dictionary with performance analysis
    """
    task_results = result.get("task_results", {})
    
    # Calculate task durations
    task_durations = {}
    for task_name, task_data in task_results.items():
        start_time = task_data.get("start_time", 0)
        end_time = task_data.get("end_time", 0)
        if start_time and end_time:
            task_durations[task_name] = end_time - start_time
    
    # Identify bottlenecks (tasks that took the longest)
    bottlenecks = sorted(task_durations.items(), key=lambda x: x[1], reverse=True)
    
    # Calculate critical path
    # (This is a simplified approach assuming the longest path is the critical path)
    dependencies = {
        task_name: task_data.get("dependencies", [])
        for task_name, task_data in task_results.items()
    }
    
    # Find tasks with no outgoing dependencies (end tasks)
    end_tasks = set(task_results.keys())
    for deps in dependencies.values():
        for dep in deps:
            if dep in end_tasks:
                end_tasks.remove(dep)
    
    # Calculate the longest path from any start task to any end task
    critical_path = []
    max_path_length = 0
    
    # For each end task, find the longest path to it
    for end_task in end_tasks:
        # Calculate all paths to this end task
        paths = []
        
        def find_paths(current_task, current_path):
            current_path = current_path + [current_task]
            if not dependencies.get(current_task, []):
                paths.append(current_path)
            else:
                for dep in dependencies.get(current_task, []):
                    find_paths(dep, current_path)
        
        find_paths(end_task, [])
        
        # Find the longest path
        for path in paths:
            path_length = sum(task_durations.get(task, 0) for task in path)
            if path_length > max_path_length:
                max_path_length = path_length
                critical_path = path
    
    # Group by agent type
    agent_durations = {}
    for task_name, task_data in task_results.items():
        agent_type = task_data.get("agent_type", "unknown")
        duration = task_durations.get(task_name, 0)
        
        if agent_type not in agent_durations:
            agent_durations[agent_type] = []
        
        agent_durations[agent_type].append(duration)
    
    # Calculate per-agent statistics
    agent_stats = {}
    for agent_type, durations in agent_durations.items():
        agent_stats[agent_type] = {
            "total_duration": sum(durations),
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "num_tasks": len(durations)
        }
    
    # Return the analysis
    return {
        "bottlenecks": bottlenecks[:5],  # Top 5 bottlenecks
        "critical_path": critical_path,
        "critical_path_duration": max_path_length,
        "agent_stats": agent_stats,
        "task_durations": task_durations
    }


if __name__ == "__main__":
    # If run directly, demonstrate visualization with sample data
    sample_result = {
        "status": "success",
        "completed_steps": ["task1", "task2", "task4"],
        "failed_steps": ["task3"],
        "retried_steps": ["task3"],
        "metrics": {
            "success_rate": 0.75,
            "execution_time": 15.5
        },
        "task_results": {
            "task1": {
                "agent_type": "file_surfer",
                "start_time": 0,
                "end_time": 3.2,
                "dependencies": []
            },
            "task2": {
                "agent_type": "web_surfer",
                "start_time": 0,
                "end_time": 5.1,
                "dependencies": []
            },
            "task3": {
                "agent_type": "terminal",
                "start_time": 5.1,
                "end_time": 7.5,
                "dependencies": ["task2"],
                "error": "Command failed with exit code 1"
            },
            "task4": {
                "agent_type": "coder",
                "start_time": 3.2,
                "end_time": 15.5,
                "dependencies": ["task1"]
            }
        }
    }
    
    # Generate visualization
    if HAS_VISUALIZATION:
        visualize_workflow(sample_result)
    
    # Generate report
    generate_workflow_report(sample_result)
    
    # Analyze performance
    analysis = analyze_workflow_performance(sample_result)
    print(json.dumps(analysis, indent=2)) 