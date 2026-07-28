# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Lab 3: Chatbot vs ReAct Agent** project for VinUni AI Codelab, demonstrating 4 levels of AI systems evolution:
- **Level 1**: Rule-based bot (historical reference)
- **Level 2**: LLM Chatbot (baseline without tools)
- **Level 3**: Reactive Agent (ReAct loop with tools) — **primary focus**
- **Level 4**: Autonomous Agent (planning + memory) — bonus section

The project teaches students to build an intelligent ReAct Agent that reasons through `Thought → Action → Observation` cycles while implementing guardrails for safety.

## Development Quick Start

### Setup
```bash
python -m venv .venv
source .venv/bin/activate          # On Windows: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

### Running the Application
```bash
python src/app.py                  # Main demo running baseline chatbot + ReAct agent
```

### Running AI Levels Demos
```bash
python src/ai_levels/level2_llm_chatbot.py      # Demo LLM chatbot baseline
python src/ai_levels/level3_reactive_agent.py   # Demo ReAct agent
python src/ai_levels/level4_autonomous_agent.py # Demo autonomous agent (bonus)
```

## Architecture & File Responsibilities

The codebase follows a **5-role team model** where each role owns a specific file:

| Role | File | Responsibility |
|------|------|-----------------|
| **Role 1: Product Architect** | `config/test_cases.json` | Define the problem scope, create 5 test cases (simple, multi-step, edge cases) |
| **Role 2: Tool Engineer** | `src/tools.py` | Declare tools/functions (e.g., `get_weather`, `search_flights`) the agent can use |
| **Role 3: Prompt Engineer** | `src/prompts.py` | Write ReAct system prompt + guardrails (MAX_ITERATIONS, TIMEOUT_SECONDS) |
| **Role 4: Core Developer** | `src/app.py` | Integrate all components: implement ReAct loop, parse actions, execute tools |
| **Role 5: Observability** | `docs/trace_eval.md` | Log traces, scoring matrix, analysis & recommendations |

## Core Architecture Pattern

The ReAct Agent loop follows this flow:

```
User Query (from test_cases.json)
    ↓
LLM generates: "Thought: ... Action: tool_name[params]"
    ↓
Action Parser extracts tool name & parameters
    ↓
Tool Executor runs the actual tool (from tools.py)
    ↓
Observation: Tool result returned to LLM
    ↓
LLM repeats: "Thought: ... Final Answer: ..."
    ↓
Output to user
```

**Key guardrails:**
- `MAX_ITERATIONS`: Prevent infinite loops (default 3)
- `TIMEOUT_SECONDS`: Timeout per tool call (default 10)
- Action parsing must be robust to malformed LLM output

## Multi-Provider LLM Support

The project uses `src/providers.py` (multi-provider adapter) to support:
- **Gemini** (Google) — `LLM_PROVIDER=gemini`
- **OpenAI** (GPT-4o, GPT-3.5-turbo) — `LLM_PROVIDER=openai`
- **Anthropic** (Claude) — `LLM_PROVIDER=anthropic`
- **OpenRouter** (unified API for multiple models) — `LLM_PROVIDER=openrouter`
- **Mock** (offline testing, no API key) — `LLM_PROVIDER=mock`

Configure in `.env`:
```
LLM_PROVIDER=gemini          # Or: openai, anthropic, openrouter, mock
GEMINI_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
OPENROUTER_API_KEY=...
LLM_MODEL=                   # Optional: override default model per provider
```

## Common Development Tasks

### Add a New Tool
1. Implement the function in `src/tools.py` with clear docstring
2. Add it to `AVAILABLE_TOOLS` dict at the bottom
3. Update `REACT_SYSTEM_PROMPT` in `src/prompts.py` to document the new tool
4. Add test cases in `config/test_cases.json` that exercise the new tool

### Modify the ReAct Prompt
Edit `src/prompts.py`:
- `CHATBOT_BASELINE_PROMPT`: System message for Level 2 (no tools)
- `REACT_SYSTEM_PROMPT`: System message for Level 3 (with tools, instructs Thought→Action format)

### Debug Agent Behavior
1. Check `docs/trace_eval.md` for logged traces
2. Add debug prints in `src/app.py` ReAct loop (around action parsing/execution)
3. Verify tool output format matches what LLM expects
4. Check if `MAX_ITERATIONS` guardrail is being hit prematurely

### Run a Specific Test Case
Modify `src/app.py` main section:
```python
sample_query = tests[N]["question"]  # Change N to test case index
```

## Key Implementation Notes

### Parsing Actions from LLM Output
The LLM is instructed to output lines like:
```
Thought: I need to check weather in Hanoi
Action: get_weather[Hà Nội]
```

The action parser must:
- Extract the tool name (`get_weather`) and params (`Hà Nội`)
- Handle malformed output gracefully (don't crash)
- Return error messages instead of raising exceptions

### Tool Function Contracts
All tools should:
- Return a string (not exception) on error: `"Error: Could not fetch weather"`
- Handle edge cases (missing data, invalid locations)
- Never crash the agent loop

### Guardrails Strategy
- **MAX_ITERATIONS**: Stops runaway loops after N steps (prevents wasted API calls)
- **TIMEOUT_SECONDS**: Timeout per tool call (prevents hanging on slow services)
- **Graceful fallback**: If tool fails, LLM should attempt to answer from knowledge or return "I cannot help"

## Testing & Evaluation

Test cases are structured in `config/test_cases.json`:
```json
[
  {
    "id": 1,
    "question": "Simple query",
    "category": "simple",
    "expected_tool": null
  },
  {
    "id": 2,
    "question": "Multi-step query requiring 2+ tools",
    "category": "multi-step",
    "expected_tool": ["tool1", "tool2"]
  }
]
```

**Scoring matrix in `docs/trace_eval.md`**:
- Agentic Fit (20%): Does the problem truly need an agent?
- ReAct Implementation (30%): Correct Thought→Action→Observation loop
- Guardrails (20%): Proper error handling & loop termination
- Cross-team testing (20%): Agent survives edge cases
- Hybrid flowchart (10%): Clear when to use chatbot vs agent

## Documentation Structure

- `README.md`: Lab overview, 4 AI levels, scoring rubric
- `docs/CODELAB.md`: Step-by-step lab guide (LMS format)
- `docs/PHAN_CONG_CONG_VIEC.md`: Role assignments & 4-milestone checklist
- `docs/trace_eval.md`: Trace logs, scoring matrix, root-cause analysis
- `docs/DANH_SACH_DE_TAI.md`: 10 suggested problem domains

## Git Workflow (Team Context)

The lab uses 4 synchronization checkpoints aligned with development milestones:

```bash
# After each milestone (Mốc):
git add .
git commit -m "Moc N: Description"
git push
```

Role 4 (Core Developer) is responsible for pulling latest changes before integration:
```bash
git pull                    # Fetch Role 1,2,3 contributions
python src/app.py          # Test integration
git push
```

## Common Pitfalls

- **Embedding tool results in chatbot system prompt**: Baseline chatbot must not know real-time data. Let it be honest ("I don't know") to show agent's advantage.
- **Model hallucinating Observations**: System prompt must instruct: application provides Observation, not the model.
- **No max iterations**: Agent loops forever if tool keeps returning non-terminating state.
- **Committing API keys**: Always use `.env` and `.gitignore` for secrets.
- **Fragile action parsing**: Handle edge cases (model formats action incorrectly, model forgets action format mid-loop).
