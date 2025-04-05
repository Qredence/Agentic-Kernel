"""CoderAgent implementation for code generation, review, and refactoring."""

from typing import Dict, Any, Optional, List
from .base import BaseAgent


class CoderAgent(Agent):
    """Agent responsible for code-related tasks using LLM capabilities."""

    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        llm: Any = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the CoderAgent.
        
        Args:
            name: The unique name of the agent
            description: A brief description of the agent's capabilities
            llm: The language model instance for code operations
            config: Configuration options including max_tokens, temperature, and supported_languages
        """
        super().__init__(name, description, config)
        self.llm = llm
        self.max_tokens = config.get("max_tokens", 2000)
        self.temperature = config.get("temperature", 0.7)
        self.supported_languages = config.get("supported_languages", ["python"])

    async def execute_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a code-related task based on the task description and context.
        
        Args:
            task_description: Description of the code task to perform
            context: Additional context including action type, language, and requirements
            
        Returns:
            Dict containing the execution results and status
        """
        if not context:
            context = {}
            
        action = context.get("action", "generate")
        language = context.get("language", "python")
        
        try:
            if action == "generate":
                result = await self.generate_code(task_description, language)
            elif action == "review":
                code = context.get("code")
                if not code:
                    raise ValueError("Code must be provided for review action")
                result = await self.review_code(code, language)
            elif action == "refactor":
                code = context.get("code")
                goals = context.get("goals", [])
                if not code:
                    raise ValueError("Code must be provided for refactor action")
                result = await self.refactor_code(code, language, goals)
            elif action == "explain":
                code = context.get("code")
                if not code:
                    raise ValueError("Code must be provided for explain action")
                result = await self.explain_code(code, language)
            else:
                raise ValueError(f"Unsupported action: {action}")
                
            return {
                "status": "success",
                "output": result
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def generate_code(self, description: str, language: str) -> Dict[str, Any]:
        """Generate code based on a description.
        
        Args:
            description: Description of what the code should do
            language: Programming language to generate code in
            
        Returns:
            Dict containing generated code, language, and explanation
        """
        if language not in self.supported_languages:
            raise ValueError(f"Unsupported language: {language}")
            
        return await self.llm.generate_code(
            description,
            language=language,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )

    async def review_code(self, code: str, language: str) -> Dict[str, Any]:
        """Review code and provide feedback.
        
        Args:
            code: Code to review
            language: Programming language of the code
            
        Returns:
            Dict containing review feedback including issues, suggestions, and quality score
        """
        if not code.strip():
            raise ValueError("Code cannot be empty")
            
        if language not in self.supported_languages:
            raise ValueError(f"Unsupported language: {language}")
            
        return await self.llm.review_code(code, language)

    async def refactor_code(
        self,
        code: str,
        language: str,
        goals: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Refactor code based on specified goals.
        
        Args:
            code: Code to refactor
            language: Programming language of the code
            goals: List of refactoring goals (e.g., "improve_readability", "reduce_complexity")
            
        Returns:
            Dict containing refactored code, changes made, and improvement metrics
        """
        if not code.strip():
            raise ValueError("Code cannot be empty")
            
        if not language:
            raise ValueError("Language must be specified")
            
        if language not in self.supported_languages:
            raise ValueError(f"Unsupported language: {language}")
            
        return await self.llm.refactor_code(
            code,
            language=language,
            goals=goals or [],
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )

    async def explain_code(self, code: str, language: str) -> Dict[str, Any]:
        """Provide a detailed explanation of code.
        
        Args:
            code: Code to explain
            language: Programming language of the code
            
        Returns:
            Dict containing explanation, complexity analysis, and key concepts
        """
        if not code.strip():
            raise ValueError("Code cannot be empty")
            
        if language not in self.supported_languages:
            raise ValueError(f"Unsupported language: {language}")
            
        return await self.llm.explain_code(code, language)

    def supports_language(self, language: str) -> bool:
        """Check if a programming language is supported.
        
        Args:
            language: Programming language to check
            
        Returns:
            True if the language is supported, False otherwise
        """
        return language in self.supported_languages

    def add_supported_language(self, language: str) -> None:
        """Add a programming language to the supported languages.
        
        Args:
            language: Programming language to add
        """
        if language not in self.supported_languages:
            self.supported_languages.append(language)

    def remove_supported_language(self, language: str) -> None:
        """Remove a programming language from the supported languages.
        
        Args:
            language: Programming language to remove
        """
        if language in self.supported_languages and language != "python":
            self.supported_languages.remove(language) 