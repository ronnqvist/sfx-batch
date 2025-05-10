# Cline Rule: Documentation Maintenance and Context Adherence for `sfx-batch`

## 1. Contextual Understanding
Before starting any new development task or modification for this project, review the following project documentation to gain full context:
- `PROJECT_PROMPT.md`: For a comprehensive understanding of the tool's purpose, CLI arguments, core functionalities, technical details (like error handling, CSV processing), dependencies, and overall structure. This is the primary source of truth for the tool's intended design and behavior.
- `README.md`: For user-facing documentation including installation, quickstart examples, API key management, and CLI usage.

## 2. Documentation Updates
After successfully implementing any changes to the tool's:
- Command-Line Interface (CLI) (e.g., arguments, options, behavior)
- Core functionalities or features (e.g., CSV parsing, filename generation, output management)
- Error handling strategy or messages
- Interaction with the `elevenlabs-sfx` library
- Dependencies or supported Python versions
- Technical structure or internal logic that impacts external understanding or usage

Ensure the following documents are updated to accurately reflect the new state of the tool:
- **`PROJECT_PROMPT.md`**: This document (or a derivative specification) should be updated if fundamental design, core requirements, or technical specifications change significantly from the original prompt.
- **`README.md`**: Update with any changes relevant to the end-user, such as new features, CLI argument changes, installation instructions, or troubleshooting tips.
- **Docstrings**: Ensure all public modules, classes, functions, and methods within the `sfx-batch` package have comprehensive and up-to-date PEP 257 compliant docstrings, particularly for `main.py` and `utils.py`.

## 3. Adherence
All development work must align with the specifications outlined in `PROJECT_PROMPT.md` and `README.md` unless explicitly instructed otherwise by the user for a specific task. If a requested change conflicts with existing documentation, bring this to the user's attention and clarify how the documentation (especially `PROJECT_PROMPT.md` or `README.md`) should be updated *prior* to implementing the change.
