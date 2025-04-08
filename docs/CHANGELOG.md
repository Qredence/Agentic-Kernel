# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation including:
  - Developer guide for the Orchestrator in `docs/developer/orchestrator.md`
  - Architecture overview in `ARCHITECTURE.md`
  - Updated README with Orchestrator details
- Python packaging rules in `.cursor/python-packager.mdc`

### Changed
- Updated task tracking in `tasks.md` with current project status
- Reorganized documentation structure with a dedicated `docs/` directory

## [0.2.0] - 2023-06-15

### Added
- Enhanced Orchestrator Agent with nested loop architecture
  - Dynamic planning capabilities for complex tasks
  - Error recovery and replanning mechanisms
  - Progress monitoring and reflection
  - Task delegation strategies
- Agent registration system for specialized agents
- Workflow state management and progress tracking
- Chainlit integration for task visualization

### Changed
- Refactored AgentSystem class to leverage dynamic planning
- Improved message handling with intelligent task complexity detection
- Enhanced task monitoring and tracking

### Fixed
- Task validation error in TaskLedger initialization
- Error handling in main application
- Agent state persistence issues between workflows

## [0.1.0] - 2023-05-30

### Added
- Initial project structure
- Base agent interface
- Task and WorkflowStep data structures
- TaskLedger and ProgressLedger for state management
- Basic Orchestrator Agent implementation
- Chainlit UI integration
- Agent System for managing agent instances
- Web Surfer Agent for web search capabilities
- File Surfer Agent for local file operations
- Chat Agent for natural language interactions 