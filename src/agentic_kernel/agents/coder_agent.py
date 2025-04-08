"""CoderAgent implementation for code generation, review, and refactoring.

This module provides an agent specialized in code-related tasks using language
models. It supports code generation, review, refactoring, and explanation across
multiple programming languages.

Key features:
    1. Code generation from natural language descriptions
    2. Code review with quality assessment
    3. Automated refactoring with customizable goals
    4. Code explanation and complexity analysis
    5. Multi-language support with dynamic language management

Example:
    .. code-block:: python

        # Initialize the coder agent
        config = AgentConfig(
            llm_mapping=LLMConfig(max_tokens=1000, temperature=0.7),
            config={"supported_languages": ["python", "typescript"]}
        )
        agent = CoderAgent(config, llm=code_llm)
        
        # Generate code
        task = Task(
            description="Create a function to calculate Fibonacci numbers",
            parameters={"action": "generate", "language": "python"}
        )
        result = await agent.execute(task)
        print(result['output']['code'])
"""

import logging
from typing import Dict, Any, Optional, List, Protocol, runtime_checkable
from dataclasses import dataclass
from enum import Enum, auto

from .base import BaseAgent, TaskCapability
from ..config import AgentConfig
from ..types import Task, TaskStatus
from ..exceptions import TaskExecutionError


logger = logging.getLogger(__name__)


class CodeAction(Enum):
    """Supported code manipulation actions.

    This enum defines the types of operations that the coder agent can perform
    on code.
    """

    GENERATE = auto()
    REVIEW = auto()
    REFACTOR = auto()
    EXPLAIN = auto()


@dataclass
class CodeResult:
    """Result of a code operation.

    This class provides a structured way to return results from code operations,
    including the code itself, any explanations or metrics, and metadata.

    Attributes:
        code (Optional[str]): The generated or modified code.
        language (str): The programming language used.
        explanation (Optional[str]): Human-readable explanation of the code.
        metrics (Optional[Dict[str, Any]]): Code quality metrics.
        suggestions (Optional[List[str]]): Improvement suggestions.
    """

    code: Optional[str]
    language: str
    explanation: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None


@runtime_checkable
class CodeLLM(Protocol):
    """Protocol defining the interface for code-capable language models.

    This protocol ensures that language models used with the coder agent
    support all necessary code operations.

    Methods:
        generate_code: Create code from a description.
        review_code: Analyze code quality and provide feedback.
        refactor_code: Modify code to meet specific goals.
        explain_code: Provide detailed code explanation.
    """

    async def generate_code(
        self, description: str, language: str, max_tokens: int, temperature: float
    ) -> CodeResult: ...

    async def review_code(self, code: str, language: str) -> CodeResult: ...

    async def refactor_code(
        self,
        code: str,
        language: str,
        goals: List[str],
        max_tokens: int,
        temperature: float,
    ) -> CodeResult: ...

    async def explain_code(self, code: str, language: str) -> CodeResult: ...


class CoderAgent(BaseAgent):
    """Agent responsible for code-related tasks using LLM capabilities.

    This agent specializes in code manipulation tasks using a language model
    that implements the CodeLLM protocol. It supports multiple programming
    languages and provides various code operations.

    The agent maintains a list of supported languages and ensures that all
    operations are performed only on supported languages.

    Attributes:
        llm (CodeLLM): Language model for code operations.
        max_tokens (int): Maximum tokens for generation tasks.
        temperature (float): Temperature for generation tasks.
        supported_languages (List[str]): Languages this agent can work with.

    Example:
        .. code-block:: python

            agent = CoderAgent(
                config=AgentConfig(...),
                llm=GPTCodeModel()
            )

            # Generate Python code
            result = await agent.generate_code(
                "Sort a list in descending order",
                "python"
            )
            print(result.code)
    """

    def __init__(self, config: AgentConfig, llm: Optional[CodeLLM] = None) -> None:
        """Initialize the CoderAgent.

        Args:
            config: Configuration parameters for the agent.
            llm: Language model instance for code operations.

        Raises:
            ValueError: If llm is None or doesn't implement CodeLLM protocol.

        Example:
            .. code-block:: python

                config = AgentConfig(
                    extra_config={
                        'plugin_config': {
                            'search_api_key': 'your-api-key',
                            'max_results': 5,
                            'timeout': 30,
                            'retry_attempts': 3
                        }
                    }
                )
                agent = WebSurferAgent(config)
        """
        super().__init__(config=config)

        if llm is None:
            raise ValueError("Language model must be provided")
        if not isinstance(llm, CodeLLM):
            raise ValueError("Language model must implement CodeLLM protocol")

        self.llm = llm
        self.max_tokens = config.llm_mapping.max_tokens
        self.temperature = config.llm_mapping.temperature
        self.supported_languages = config.config.get("supported_languages", ["python"])

    async def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a code-related task based on the task description and context.

        This method dispatches the task to the appropriate handler based on the
        action specified in the task parameters.

        Args:
            task: Task containing the code operation details.

        Returns:
            Dictionary containing:
                - status: TaskStatus indicating success or failure.
                - output: CodeResult containing operation results.
                - error: Error message if the operation failed.

        Raises:
            ValueError: If required parameters are missing or invalid.

        Example:
            .. code-block:: python

                task = Task(
                    description="Create a binary search function",
                    parameters={
                        "action": "generate",
                        "language": "python"
                    }
                )
                result = await agent.execute(task)
                if result["status"] == TaskStatus.completed:
                    print(result["output"].code)
        """
        try:
            # Extract task parameters
            action = task.parameters.get("action", "generate")
            language = task.parameters.get("language", "python")

            # Validate language
            if language not in self.supported_languages:
                raise ValueError(f"Unsupported language: {language}")

            # Dispatch to appropriate handler
            if action == CodeAction.GENERATE.name.lower():
                result = await self.generate_code(task.description, language)
            elif action == CodeAction.REVIEW.name.lower():
                code = task.parameters.get("code")
                if not code:
                    raise ValueError("Code must be provided for review action")
                result = await self.review_code(code, language)
            elif action == CodeAction.REFACTOR.name.lower():
                code = task.parameters.get("code")
                goals = task.parameters.get("goals", [])
                if not code:
                    raise ValueError("Code must be provided for refactor action")
                result = await self.refactor_code(code, language, goals)
            elif action == CodeAction.EXPLAIN.name.lower():
                code = task.parameters.get("code")
                if not code:
                    raise ValueError("Code must be provided for explain action")
                result = await self.explain_code(code, language)
            else:
                raise ValueError(f"Unsupported action: {action}")

            return {"status": TaskStatus.completed, "output": result}
        except Exception as e:
            logger.error(f"Code task execution failed: {str(e)}", exc_info=True)
            return {"status": TaskStatus.failed, "error": str(e)}

    async def generate_code(self, description: str, language: str) -> CodeResult:
        """Generate code based on a description.

        This method uses the language model to generate code that implements
        the functionality described in natural language.

        Args:
            description: Natural language description of desired functionality.
            language: Programming language to generate code in.

        Returns:
            CodeResult containing:
                - code: The generated code.
                - language: The programming language used.
                - explanation: Description of how the code works.

        Raises:
            ValueError: If language is not supported.
            TaskExecutionError: If code generation fails.

        Example:
            .. code-block:: python

                result = await agent.generate_code(
                    "Create a function that reverses a string",
                    "python"
                )
                print(result.code)
                print(result.explanation)
        """
        if language not in self.supported_languages:
            raise ValueError(f"Unsupported language: {language}")

        try:
            return await self.llm.generate_code(
                description,
                language=language,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
        except Exception as e:
            raise TaskExecutionError(f"Code generation failed: {str(e)}")

    async def review_code(self, code: str, language: str) -> CodeResult:
        """Review code and provide feedback.

        This method analyzes code quality, identifies potential issues,
        and provides improvement suggestions.

        Args:
            code: Source code to review.
            language: Programming language of the code.

        Returns:
            CodeResult containing:
                - metrics: Code quality metrics.
                - suggestions: List of improvement suggestions.
                - explanation: Detailed review feedback.

        Raises:
            ValueError: If code is empty or language not supported.
            TaskExecutionError: If code review fails.

        Example:
            .. code-block:: python

                result = await agent.review_code(
                    "def add(a,b): return a+b",
                    "python"
                )
                for suggestion in result.suggestions:
                    print(f"- {suggestion}")
        """
        if not code.strip():
            raise ValueError("Code cannot be empty")

        if language not in self.supported_languages:
            raise ValueError(f"Unsupported language: {language}")

        try:
            return await self.llm.review_code(code, language)
        except Exception as e:
            raise TaskExecutionError(f"Code review failed: {str(e)}")

    async def refactor_code(
        self, code: str, language: str, goals: Optional[List[str]] = None
    ) -> CodeResult:
        """Refactor code based on specified goals.

        This method modifies code to improve its quality according to the
        specified refactoring goals while maintaining its functionality.

        Args:
            code: Source code to refactor.
            language: Programming language of the code.
            goals: Refactoring objectives (e.g., "improve_readability").

        Returns:
            CodeResult containing:
                - code: The refactored code.
                - explanation: Description of changes made.
                - metrics: Improvement metrics.

        Raises:
            ValueError: If code is empty or language not supported.
            TaskExecutionError: If refactoring fails.

        Example:
            .. code-block:: python

                result = await agent.refactor_code(
                    "def f(x): return x*2",
                    "python",
                    goals=["improve_readability", "add_docstring"]
                )
                print("Before:", code)
                print("After:", result.code)
                print("Changes:", result.explanation)
        """
        if not code.strip():
            raise ValueError("Code cannot be empty")

        if not language:
            raise ValueError("Language must be specified")

        if language not in self.supported_languages:
            raise ValueError(f"Unsupported language: {language}")

        try:
            return await self.llm.refactor_code(
                code,
                language=language,
                goals=goals or [],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
        except Exception as e:
            raise TaskExecutionError(f"Code refactoring failed: {str(e)}")

    async def explain_code(self, code: str, language: str) -> CodeResult:
        """Provide a detailed explanation of code.

        This method analyzes code and generates a human-readable explanation
        of its functionality, including complexity analysis and key concepts.

        Args:
            code: Source code to explain.
            language: Programming language of the code.

        Returns:
            CodeResult containing:
                - explanation: Detailed code explanation.
                - metrics: Complexity metrics.

        Raises:
            ValueError: If code is empty or language not supported.
            TaskExecutionError: If explanation fails.

        Example:
            .. code-block:: python

                result = await agent.explain_code(
                    "def quicksort(arr): ...",
                    "python"
                )
                print(result.explanation)
                print("Time complexity:", result.metrics["complexity"])
        """
        if not code.strip():
            raise ValueError("Code cannot be empty")

        if language not in self.supported_languages:
            raise ValueError(f"Unsupported language: {language}")

        try:
            return await self.llm.explain_code(code, language)
        except Exception as e:
            raise TaskExecutionError(f"Code explanation failed: {str(e)}")

    def supports_language(self, language: str) -> bool:
        """Check if a programming language is supported.

        Args:
            language: Programming language to check.

        Returns:
            True if the language is supported, False otherwise.

        Example:
            .. code-block:: python

                if agent.supports_language("rust"):
                    result = await agent.generate_code(description, "rust")
                else:
                    print("Rust is not supported")
        """
        return language in self.supported_languages

    def add_supported_language(self, language: str) -> None:
        """Add a programming language to the supported languages.

        This method expands the agent's capabilities by adding support
        for a new programming language.

        Args:
            language: Programming language to add.

        Example:
            .. code-block:: python

                agent.add_supported_language("go")
                assert agent.supports_language("go")
        """
        if language not in self.supported_languages:
            self.supported_languages.append(language)
            logger.info(f"Added support for {language}")

    def remove_supported_language(self, language: str) -> None:
        """Remove a programming language from supported languages.

        This method restricts the agent's capabilities by removing support
        for a programming language.

        Args:
            language: Programming language to remove.

        Example:
            .. code-block:: python

                agent.remove_supported_language("javascript")
                assert not agent.supports_language("javascript")
        """
        if language in self.supported_languages:
            self.supported_languages.remove(language)
            logger.info(f"Removed support for {language}")

    def _get_supported_tasks(self) -> Dict[str, TaskCapability]:
        """Get the tasks supported by this agent.

        Returns:
            Dictionary mapping task types to their capabilities.

        Example:
            .. code-block:: python

                capabilities = agent._get_supported_tasks()
                for task_type, details in capabilities.items():
                    print(f"{task_type}:")
                    print(f"  Description: {details['description']}")
                    print(f"  Parameters: {details['parameters']}")
        """
        return {
            "generate_code": {
                "description": "Generate code from natural language description",
                "parameters": ["description", "language"],
                "optional_parameters": ["max_tokens", "temperature"],
                "examples": [
                    {
                        "description": "Create a function to calculate factorial",
                        "language": "python",
                        "max_tokens": 500,
                        "temperature": 0.7,
                    }
                ],
            },
            "review_code": {
                "description": "Review code and provide feedback",
                "parameters": ["code", "language"],
                "optional_parameters": [],
                "examples": [
                    {"code": "def add(a,b): return a+b", "language": "python"}
                ],
            },
            "refactor_code": {
                "description": "Refactor code based on specified goals",
                "parameters": ["code", "language"],
                "optional_parameters": ["goals"],
                "examples": [
                    {
                        "code": "def f(x): return x*2",
                        "language": "python",
                        "goals": ["improve_readability", "add_docstring"],
                    }
                ],
            },
            "explain_code": {
                "description": "Provide detailed code explanation",
                "parameters": ["code", "language"],
                "optional_parameters": [],
                "examples": [
                    {"code": "def binary_search(arr, x): ...", "language": "python"}
                ],
            },
        }
