# AI Agent Persona & Operational Rules

## 1. Organic Documentation Workflow (Core Directive)
You must follow the "Organic Documentation" lifecycle for every task. **All documentation must be written in Korean.**

1.  **Read Context**: Before generating code, always cross-reference `SPEC.md` (Project Specs) and `PROGRESS.md` (Task Status).
    *   **Transparency Check**: When creating an `implementation_plan.md` or stating the task, **explicitly cite** which rules from `.ai/RULES.md` you are applying (e.g., "Applying `No TypeScript` rule").
2.  **Reverse Interview (Start)**: If `SPEC.md` is empty, incomplete, or the user's request is ambiguous:
    * Do NOT guess.
    * Initiate a "Reverse Interview" to gather necessary requirements.
    * Summarize the answers and update `SPEC.md` (in Korean) immediately.
3.  **Execute & Update (Cycle)**:
    * **Code**: Implement the feature/fix.
    * **Test**: Verify the changes (run tests, manual check).
    * **Document**: Update `PROGRESS.md` and other docs (in Korean) to reflect the change.
    *   **Deploy**: Deploy the changes if applicable/requested.
4.  **Report & Verify (Finish)**:
    *   **Post-Task Transparency**: When notifying the user of completion, **explicitly state** which rules were applied and provide evidence (e.g., "Verified `No TypeScript` rule by checking standard `package.json`").

## 2. File Management Rules

### `SPEC.md` (The Blueprint)
* **Purpose**: Stores the "Source of Truth" (Goals, Tech Stack, Database Schema, API Constraints).
* **Action**: Update this file ONLY when requirements change or are clarified through conversation.

### `PROGRESS.md` (The Tracker)
* **Purpose**: Tracks the development lifecycle.
* **Structure**:
    * `[ ]` Todo
    * `[x]` Completed
    * **Current Phase**: What is being worked on right now.
* **Action**: You have permission to edit this file proactively. If a new sub-task arises during coding, add it here.

## 3. Coding Standards
* **Environment**: VS Code (optimize for this editor).
* **Style**: Clean, modular backend code. Prefer automation scripts over manual steps.
* **Language**: (Preferred language, e.g., Python/Node.js) unless specified otherwise.
* **Tech Stack**: Python 3.10+, FastAPI, Celery, Redis, PostgreSQL (Async), LangChain.

## 4. Interaction Protocol
* If I ask "What's next?", look at `PROGRESS.md` and suggest the next logical step.
* If I provide a vague idea, propose a draft structure for `SPEC.md` first.

## 5. Technical Constraints & Style (Dynamic)
* **Rule**: You must dynamically adapt to the project's specific constants.
* **Source of Truth**: Always read `.ai/RULES.md` and `.ai/ARCHITECTURE.md` in the current workspace root.
