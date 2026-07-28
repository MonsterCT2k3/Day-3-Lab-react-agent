"""
MOC 4: TRÌNH CHIẾU APP - CLI INTERFACE CHUYÊN NGHIỆP
Hiển thị từng bước agent rõ ràng, dễ follow, không màu mè.
"""

import json
import os
import sys
from dotenv import load_dotenv
import re
import time
from datetime import datetime

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
        for line in lines[:5]:  # First 5 lines
            print(f"  OBSERVATION: {line}")
        if len(lines) > 5:
            print(f"  OBSERVATION: ... ({len(lines)-5} more lines)")

    @staticmethod
    def final_answer(text):
        lines = text.split('\n')
        for line in lines[:10]:
            print(f"  FINAL ANSWER: {line}")
        if len(lines) > 10:
            print(f"  FINAL ANSWER: ... ({len(lines)-10} more lines)")

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
    """Parse Action from LLM output - robust version"""
    # Try format: Action: tool_name(param1, param2, ...)
    match = re.search(r'Action\s*:\s*(\w+)\s*\((.*?)\)', text, re.DOTALL)
    if match:
        tool_name = match.group(1).strip()
        params_str = match.group(2).strip()
        params = []
        if params_str:
            params = [p.strip().strip('"\'') for p in params_str.split(',')]
        return tool_name, params

    # Try format: Action: tool_name[param1, param2, ...]
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
    Logger.section(f"CHATBOT BASELINE: {query}")
    Logger.config("System Prompt", "Knowledge-based (no real-time data)")

    response = provider.generate(query, system_prompt=CHATBOT_BASELINE_PROMPT)
    Logger.input_log("RESPONSE", response)

# ============================================================================
# DEMO: REACT AGENT
# ============================================================================

def demo_react_agent(query, provider, test_id=None):
    """Demo: ReAct Agent with full logging"""
    Logger.section(f"REACT AGENT: {query}")
    Logger.config("Max Iterations", MAX_ITERATIONS)
    Logger.config("Timeout Per Tool", f"{TIMEOUT_SECONDS}s")

    conversation = f"User: {query}\n\n"
    step = 0

    while step < MAX_ITERATIONS:
        step += 1
        Logger.step(step, MAX_ITERATIONS, "Generate Thought and Action")

        full_prompt = REACT_SYSTEM_PROMPT + conversation
        if hasattr(provider, 'chat'):
            llm_output = provider.chat(query, conversation)
        else:
            llm_output = provider.generate(full_prompt)

        # Extract thought
        thought_match = re.search(r'Thought\s*:\s*(.*?)(?:Action\s*:|$)', llm_output, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip().split('\n')[0]
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
            Logger.error("No valid Action found in LLM output")
            conversation += "System: Please format action as 'Action: tool_name(param1, param2, ...)'\n\n"
            continue

        Logger.action(tool_name, params)

        # Check tool exists
        if tool_name not in TOOL_REGISTRY:
            available = ", ".join(TOOL_REGISTRY.keys())
            Logger.error(f"Tool not in registry. Available: {available}")
            conversation += f"Observation: Tool '{tool_name}' not found.\n\n"
            continue

        # Execute tool
        success, result = execute_tool(tool_name, params)
        Logger.observation(result)

        conversation += f"Observation: {result}\n\n"

    if step >= MAX_ITERATIONS:
        Logger.guardrail(f"Reached max iterations ({MAX_ITERATIONS}). Stopping loop.")

# ============================================================================
# INTERACTIVE MENU
# ============================================================================

def display_menu():
    Logger.header("MOC 4: CROSS AUDIT & DEMO")
    print("Select a test case or action:")
    print()
    tests = load_test_cases()
    for i, test in enumerate(tests, 1):
        category = test.get("category", "Unknown")
        question = test["question"]
        print(f"  [{i}] {category}")
        print(f"      {question}")
        print()
    print("  [0] Run all test cases")
    print("  [c] Custom question (enter your own)")
    print("  [q] Quit")
    print()

def run_all_tests(provider):
    """Run all test cases with both baseline and agent"""
    tests = load_test_cases()

    Logger.header(f"RUNNING ALL {len(tests)} TEST CASES")

    results = {
        "passed": 0,
        "failed": 0,
        "timeout": 0,
        "errors": []
    }

    for idx, test in enumerate(tests, 1):
        try:
            Logger.section(f"Test Case {idx}: {test.get('category', 'Unknown')}")
            Logger.input_log("Question", test["question"])
            Logger.input_log("Expected Behavior", test.get("expected_behavior", "N/A")[:100])

            print("\n  --- BASELINE RESPONSE ---")
            demo_chatbot_baseline(test["question"], provider)

            print("\n  --- AGENT RESPONSE ---")
            demo_react_agent(test["question"], provider, test_id=idx)

            results["passed"] += 1
            Logger.success(f"Test case {idx} completed")

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"Test {idx}: {str(e)}")
            Logger.error(f"Test case {idx} failed: {str(e)}")

    # Summary
    Logger.header("TEST RESULTS SUMMARY")
    print(f"  Total Test Cases: {len(tests)}")
    print(f"  Passed: {results['passed']}")
    print(f"  Failed: {results['failed']}")
    print()
    if results["errors"]:
        print("  Errors:")
        for error in results["errors"]:
            print(f"    - {error}")

def interactive_demo(provider):
    """Interactive test case runner"""
    display_menu()

    while True:
        choice = input("Enter choice (0-10, c, or q): ").strip().lower()

        if choice == 'q':
            print("\nGoodbye!")
            break
        elif choice == '0':
            run_all_tests(provider)
        elif choice == 'c':
            custom_question = input("\nEnter your custom question: ").strip()
            if custom_question:
                Logger.section(f"CUSTOM QUESTION")
                Logger.input_log("Question", custom_question)

                print("\n  --- BASELINE RESPONSE ---")
                demo_chatbot_baseline(custom_question, provider)

                print("\n  --- AGENT RESPONSE ---")
                demo_react_agent(custom_question, provider, test_id=None)
            else:
                print("Question cannot be empty")
        else:
            try:
                idx = int(choice) - 1
                tests = load_test_cases()
                if 0 <= idx < len(tests):
                    test = tests[idx]
                    Logger.section(f"Test Case {idx+1}: {test.get('category', 'Unknown')}")
                    Logger.input_log("Question", test["question"])
                    Logger.input_log("Expected Behavior", test.get("expected_behavior", "N/A"))

                    print("\n  --- BASELINE RESPONSE ---")
                    demo_chatbot_baseline(test["question"], provider)

                    print("\n  --- AGENT RESPONSE ---")
                    demo_react_agent(test["question"], provider, test_id=idx+1)
                else:
                    print("Invalid test case number")
            except ValueError:
                print("Invalid input")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    Logger.header("MOC 4: DEMONSTRATION & CROSS AUDIT")

    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")

    Logger.section("CONFIGURATION")
    Logger.config("LLM Provider", provider.__class__.__name__)
    Logger.config("LLM Model", model_name)
    Logger.config("Max Iterations", MAX_ITERATIONS)
    Logger.config("Timeout Per Tool", f"{TIMEOUT_SECONDS}s")

    tests = load_test_cases()
    Logger.config("Test Cases Loaded", len(tests))

    print("\n")
    interactive_demo(provider)
