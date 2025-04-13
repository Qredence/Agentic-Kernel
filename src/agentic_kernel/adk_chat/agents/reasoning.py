"""Reasoning Agent for the ADK A2A Chat System."""

import asyncio
import logging
from typing import Any

from google.adk.tools import FunctionTool

from ..utils.adk_a2a_utils import ADKA2AAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReasoningAgent(ADKA2AAgent):
    """Reasoning Agent that performs logical reasoning and analysis."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8003,
    ):
        """Initialize the ReasoningAgent.

        Args:
            host: The host for the A2A server
            port: The port for the A2A server
        """
        super().__init__(
            name="reasoning",
            description="Reasoning Agent that performs logical reasoning and analysis",
            model="gemini-2.0-flash-exp",
            host=host,
            port=port,
        )

        # Add tools for reasoning
        self.add_tool(
            FunctionTool(
                name="analyze_problem",
                description="Analyze a problem and provide logical reasoning",
                function=self.analyze_problem,
            ),
        )

        self.add_tool(
            FunctionTool(
                name="evaluate_options",
                description="Evaluate different options and provide recommendations",
                function=self.evaluate_options,
            ),
        )

        self.add_tool(
            FunctionTool(
                name="explain_concept",
                description="Explain a concept with clear logical reasoning",
                function=self.explain_concept,
            ),
        )

        # Register A2A methods
        self.register_a2a_method("tasks.send", self.handle_tasks_send)
        self.register_a2a_method("tasks.get", self.handle_tasks_get)

    async def analyze_problem(self, problem: str) -> dict[str, Any]:
        """Analyze a problem and provide logical reasoning.

        Args:
            problem: The problem to analyze

        Returns:
            Analysis of the problem
        """
        logger.info(f"Analyzing problem: {problem}")

        # This is a simplified implementation
        # In a real system, this would use the ADK agent to analyze the problem

        # Simulate analysis delay
        await asyncio.sleep(1)

        # Generate a mock analysis
        analysis = (
            f"Analysis of the problem '{problem}':\n\n"
            f"1. Key aspects of the problem:\n"
            f"   - [Identified aspect 1]\n"
            f"   - [Identified aspect 2]\n\n"
            f"2. Logical breakdown:\n"
            f"   - [Logical step 1]\n"
            f"   - [Logical step 2]\n\n"
            f"3. Conclusion:\n"
            f"   [Reasoned conclusion based on the analysis]"
        )

        return {
            "problem": problem,
            "analysis": analysis,
            "confidence": 0.85,
        }

    async def evaluate_options(
        self,
        problem: str,
        options: list[str],
    ) -> dict[str, Any]:
        """Evaluate different options and provide recommendations.

        Args:
            problem: The problem context
            options: List of options to evaluate

        Returns:
            Evaluation of the options
        """
        logger.info(f"Evaluating options for problem: {problem}")

        # This is a simplified implementation
        # In a real system, this would use the ADK agent to evaluate the options

        # Simulate evaluation delay
        await asyncio.sleep(1)

        # Generate mock evaluations
        evaluations = []
        for i, option in enumerate(options):
            evaluations.append(
                {
                    "option": option,
                    "pros": [f"Pro {i + 1}.1", f"Pro {i + 1}.2"],
                    "cons": [f"Con {i + 1}.1"],
                    "score": 0.5 + (i * 0.1),  # Just for demonstration
                }
            )

        # Sort by score
        evaluations.sort(key=lambda x: x["score"], reverse=True)

        # Select the recommended option
        recommended = evaluations[0]["option"] if evaluations else None

        return {
            "problem": problem,
            "evaluations": evaluations,
            "recommended": recommended,
        }

    async def explain_concept(self, concept: str) -> dict[str, Any]:
        """Explain a concept with clear logical reasoning.

        Args:
            concept: The concept to explain

        Returns:
            Explanation of the concept
        """
        logger.info(f"Explaining concept: {concept}")

        # This is a simplified implementation
        # In a real system, this would use the ADK agent to explain the concept

        # Simulate explanation delay
        await asyncio.sleep(1)

        # Generate a mock explanation
        explanation = (
            f"Explanation of '{concept}':\n\n"
            f"Definition: [Clear definition of the concept]\n\n"
            f"Key principles:\n"
            f"1. [First principle]\n"
            f"2. [Second principle]\n\n"
            f"Examples:\n"
            f"- [Example 1]\n"
            f"- [Example 2]\n\n"
            f"Related concepts: [Related concept 1], [Related concept 2]"
        )

        return {
            "concept": concept,
            "explanation": explanation,
            "complexity_level": "intermediate",
        }

    async def handle_tasks_send(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle an A2A tasks.send request.

        Args:
            params: The request parameters

        Returns:
            The response
        """
        logger.info(f"Received tasks.send request: {params}")

        # Extract task information
        description = params.get("description", "")
        task_input = params.get("input", {})

        # Process based on the task description
        if "reasoning" in description.lower() or "analyze" in description.lower():
            problem = task_input.get("problem", "")

            # Check if options are provided for evaluation
            options = task_input.get("options", [])
            if options:
                result = await self.evaluate_options(problem, options)
                return {
                    "status": "completed",
                    "analysis": f"Evaluated {len(options)} options. Recommended: {result['recommended']}",
                    "evaluations": result["evaluations"],
                    "recommended": result["recommended"],
                }

            # Check if it's a concept explanation
            if "explain" in description.lower() or "concept" in description.lower():
                concept = task_input.get("concept", problem)
                result = await self.explain_concept(concept)
                return {
                    "status": "completed",
                    "analysis": result["explanation"],
                    "complexity_level": result["complexity_level"],
                }

            # Default to problem analysis
            result = await self.analyze_problem(problem)
            return {
                "status": "completed",
                "analysis": result["analysis"],
                "confidence": result["confidence"],
            }

        # Default response for unknown tasks
        return {
            "status": "failed",
            "error": f"Unknown task type: {description}",
        }

    async def handle_tasks_get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle an A2A tasks.get request.

        Args:
            params: The request parameters

        Returns:
            The response
        """
        logger.info(f"Received tasks.get request: {params}")

        # Extract task ID
        task_id = params.get("task_id", "")

        # This is a simplified implementation
        # In a real system, this would retrieve the task status from a database

        return {
            "task_id": task_id,
            "status": "completed",
            "analysis": "Reasoning analysis for the requested task",
            "confidence": 0.9,
        }
