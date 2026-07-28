"""
MOC 4: AUTOMATIC DEMO - NON-INTERACTIVE
Chạy tự động với test case được chỉ định từ command line.
"""

import json
import os
import sys
from dotenv import load_dotenv
import re
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from tools import TOOL_REGISTRY
from prompts import CHATBOT_BASELINE_PROMPT, REACT_SYSTEM_PROMPT, MAX_ITERATIONS, TIMEOUT_SECONDS
from providers import get_llm_provider

load_dotenv()

# ============================================================================
# UTILITY: LOGGING & FORMATTING
# ============================================================================

class Logger:
    """Clean, professional logging without emojis"""

    @staticmethod
    def header(text, width=70):
        print(f"\n{'='*width}")
        print(f"{text.center(width)}")
        print(f"{'='*width}\n")

    @staticmethod
    def section(text):
        print(f"\n{'-'*70}")
        print(f"  {text}")
        print(f"{'-'*70}\n")

    @staticmethod
    def step(step_num, max_steps, text):
        print(f"[STEP {step_num}/{max_steps}] {text}")

    @staticmethod
    def input_log(label, value):
        print(f"  [{label}] {value}")

    @staticmethod
    def thought(text):
        print(f"  THOUGHT: {text}")

    @staticmethod
    def action(tool_name, params):
        print(f"  ACTION: {tool_name}({', '.join(repr(p) for p in params)})")

    @staticmethod
    def observation(text):
        lines = text.split('\n')
        print(f"  OBSERVATION:")
        for line in lines[:3]:
            print(f"    {line}")
        if len(lines) > 3:
            print(f"    ... ({len(lines)-3} more lines)")

    @staticmethod
    def final_answer(text):
        lines = text.split('\n')
        print(f"  FINAL ANSWER:")
        for line in lines[:5]:
            print(f"    {line}")
        if len(lines) > 5:
            print(f"    ... ({len(lines)-5} more lines)")

    @staticmethod
    def error(text):
        print(f"  ERROR: {text}")

    @staticmethod
    def success(text):
        print(f"  SUCCESS: {text}")

    @staticmethod
    def guardrail(text):
        print(f"  [GUARDRAIL] {text}")

    @staticmethod
    def config(label, value):
        print(f"  CONFIG: {label} = {value}")

# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def load_test_cases():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")

    if not os.path.exists(config_path):
        config_path = "test_cases.json"

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_action(text: str):
    """Parse Action from LLM output"""
    match = re.search(r'Action\s*:\s*(\w+)\s*\((.*?)\)', text, re.DOTALL)
    if match:
        tool_name = match.group(1).strip()
        params_str = match.group(2).strip()
        params = []
        if params_str:
            params = [p.strip().strip('"\'') for p in params_str.split(',')]
        return tool_name, params

    match = re.search(r'Action\s*:\s*(\w+)\s*\[(.*?)\]', text, re.DOTALL)
    if match:
        tool_name = match.group(1).strip()
        params_str = match.group(2).strip()
        params = []
        if params_str:
            params = [p.strip().strip('"\'') for p in params_str.split(',')]
        return tool_name, params

    return None, []

def execute_tool(tool_name: str, params: list) -> tuple:
    """Execute tool and return (success: bool, result: str)"""
    if tool_name not in TOOL_REGISTRY:
        return False, f"Tool '{tool_name}' not found in registry"

    tool_func = TOOL_REGISTRY[tool_name]
    try:
        start_time = time.time()
        result = tool_func(*params) if params else tool_func()
        elapsed = time.time() - start_time

        if elapsed > TIMEOUT_SECONDS:
            return False, f"Timeout: Tool exceeded {TIMEOUT_SECONDS}s"

        return True, str(result)
    except Exception as e:
        return False, f"Exception: {str(e)}"

# ============================================================================
# DEMO: CHATBOT BASELINE
# ============================================================================

def demo_chatbot_baseline(query, provider):
    """Demo: Simple chatbot without tools"""
    Logger.section(f"CHATBOT BASELINE")
    Logger.input_log("Question", query)
    Logger.config("Mode", "Knowledge-based (no real-time data)")

    response = provider.generate(query, system_prompt=CHATBOT_BASELINE_PROMPT)
    Logger.input_log("Response", response[:200] + ("..." if len(response) > 200 else ""))

# ============================================================================
# DEMO: REACT AGENT
# ============================================================================

def demo_react_agent(query, provider):
    """Demo: ReAct Agent with full logging"""
    Logger.section(f"REACT AGENT")
    Logger.input_log("Question", query)
    Logger.config("Max Iterations", MAX_ITERATIONS)
    Logger.config("Timeout Per Tool", f"{TIMEOUT_SECONDS}s")

    conversation = f"User: {query}\n\n"
    step = 0
    total_steps = 0
    max_steps_display = MAX_ITERATIONS

    while step < MAX_ITERATIONS:
        step += 1
        total_steps += 1
        Logger.step(step, max_steps_display, "Processing")

        full_prompt = REACT_SYSTEM_PROMPT + conversation
        if hasattr(provider, 'chat'):
            llm_output = provider.chat(query, conversation)
        else:
            llm_output = provider.generate(full_prompt)

        # Extract thought
        thought_match = re.search(r'Thought\s*:\s*(.*?)(?:Action\s*:|$)', llm_output, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip().split('\n')[0][:100]
            Logger.thought(thought)

        conversation += llm_output + "\n"

        # Check for final answer
        if "Final Answer:" in llm_output or "Câu trả lời cuối cùng:" in llm_output:
            final_match = re.search(r'(?:Final Answer|Câu trả lời cuối cùng)\s*:\s*(.*)', llm_output, re.DOTALL)
            if final_match:
                Logger.final_answer(final_match.group(1).strip())
            Logger.success("Agent reached Final Answer")
            break

        # Parse action
        tool_name, params = parse_action(llm_output)

        if not tool_name:
            Logger.error("No valid Action format found")
            conversation += "System: Please use format 'Action: tool_name(param1, param2, ...)'\n\n"
            continue

        Logger.action(tool_name, params)

        # Check tool exists
        if tool_name not in TOOL_REGISTRY:
            available = list(TOOL_REGISTRY.keys())[:3]
            Logger.error(f"Tool not found. Available: {', '.join(available)}...")
            conversation += f"Observation: Tool '{tool_name}' not found.\n\n"
            continue

        # Execute tool
        success, result = execute_tool(tool_name, params)
        if success:
            Logger.success(f"Tool executed successfully")
        else:
            Logger.error(f"Tool execution failed")
        Logger.observation(result)

        conversation += f"Observation: {result}\n\n"

    if step >= MAX_ITERATIONS:
        Logger.guardrail(f"Reached max iterations ({MAX_ITERATIONS}). Stopping loop.")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    Logger.header("MOC 4: AUTOMATIC DEMONSTRATION")

    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")

    Logger.section("CONFIGURATION")
    Logger.config("LLM Provider", provider.__class__.__name__)
    Logger.config("LLM Model", model_name)
    Logger.config("Max Iterations", MAX_ITERATIONS)
    Logger.config("Timeout Per Tool", f"{TIMEOUT_SECONDS}s")

    tests = load_test_cases()
    Logger.config("Test Cases Available", len(tests))

    # Parse command line argument
    test_num = 1
    if len(sys.argv) > 1:
        try:
            test_num = int(sys.argv[1])
            if test_num < 1 or test_num > len(tests):
                print(f"Invalid test case number. Available: 1-{len(tests)}")
                sys.exit(1)
        except ValueError:
            print(f"Usage: python demo_moc4_auto.py [test_case_number]")
            print(f"Example: python demo_moc4_auto.py 3")
            print(f"Available test cases: 1-{len(tests)}")
            sys.exit(1)

    test = tests[test_num - 1]

    Logger.header(f"TEST CASE {test_num}: {test.get('category', 'Unknown')}")
    Logger.input_log("Expected Behavior", test.get("expected_behavior", "N/A"))

    # Run both baseline and agent
    print("\n\n")
    demo_chatbot_baseline(test["question"], provider)

    print("\n\n")
    demo_react_agent(test["question"], provider)

    Logger.header("DEMONSTRATION COMPLETE")
    print()
