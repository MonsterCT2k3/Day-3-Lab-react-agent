"""
MOC 4: VSCODE-STYLE CLI INTERFACE
Display steps clearly like VSCode debug console, then final answer
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

class VSCodeLogger:
    """VSCode-style console output"""

    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    GRAY = '\033[90m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    @staticmethod
    def clear():
        os.system('clear' if os.name == 'posix' else 'cls')

    @staticmethod
    def header(text):
        width = 80
        print(f"\n{VSCodeLogger.BOLD}{VSCodeLogger.BLUE}{'='*width}{VSCodeLogger.RESET}")
        print(f"{VSCodeLogger.BOLD}{VSCodeLogger.BLUE}{text.center(width)}{VSCodeLogger.RESET}")
        print(f"{VSCodeLogger.BOLD}{VSCodeLogger.BLUE}{'='*width}{VSCodeLogger.RESET}\n")

    @staticmethod
    def section(label, value):
        print(f"{VSCodeLogger.GRAY}[{label}]{VSCodeLogger.RESET} {value}")

    @staticmethod
    def step_start(step_num, max_steps):
        print(f"\n{VSCodeLogger.BLUE}{VSCodeLogger.BOLD}▶ STEP {step_num}/{max_steps}{VSCodeLogger.RESET}")
        print(f"{VSCodeLogger.GRAY}{'─'*76}{VSCodeLogger.RESET}")

    @staticmethod
    def thought(text):
        print(f"{VSCodeLogger.YELLOW}├─ THOUGHT:{VSCodeLogger.RESET}")
        lines = text.split('\n')
        for i, line in enumerate(lines):
            prefix = "│  " if i < len(lines) - 1 else "│  "
            print(f"{VSCodeLogger.YELLOW}{prefix}{VSCodeLogger.RESET}{line}")

    @staticmethod
    def action(tool_name, params):
        print(f"{VSCodeLogger.GREEN}├─ ACTION:{VSCodeLogger.RESET}")
        param_str = ", ".join(f'"{p}"' for p in params) if params else ""
        action_line = f"{tool_name}({param_str})"
        print(f"{VSCodeLogger.GREEN}│  {VSCodeLogger.BOLD}{action_line}{VSCodeLogger.RESET}")

    @staticmethod
    def observation(text):
        print(f"{VSCodeLogger.BLUE}├─ OBSERVATION:{VSCodeLogger.RESET}")
        lines = text.split('\n')
        max_lines = 5
        for i, line in enumerate(lines[:max_lines]):
            is_last = (i == max_lines - 1 or i == len(lines) - 1)
            prefix = "│  "
            print(f"{VSCodeLogger.BLUE}{prefix}{VSCodeLogger.RESET}{line[:100]}")
        if len(lines) > max_lines:
            print(f"{VSCodeLogger.BLUE}│  {VSCodeLogger.GRAY}... ({len(lines)-max_lines} more lines){VSCodeLogger.RESET}")

    @staticmethod
    def error(text):
        print(f"{VSCodeLogger.RED}├─ ERROR:{VSCodeLogger.RESET}")
        print(f"{VSCodeLogger.RED}│  {text}{VSCodeLogger.RESET}")

    @staticmethod
    def guardrail(text):
        print(f"\n{VSCodeLogger.YELLOW}{VSCodeLogger.BOLD}⚠  GUARDRAIL: {text}{VSCodeLogger.RESET}")

    @staticmethod
    def final_answer_header():
        print(f"\n{VSCodeLogger.GREEN}{VSCodeLogger.BOLD}✓ FINAL ANSWER{VSCodeLogger.RESET}")
        print(f"{VSCodeLogger.GREEN}{'─'*76}{VSCodeLogger.RESET}")

    @staticmethod
    def final_answer(text):
        lines = text.split('\n')
        for line in lines[:20]:
            if line.strip():
                print(f"{VSCodeLogger.WHITE}{line}{VSCodeLogger.RESET}")
        if len(lines) > 20:
            print(f"{VSCodeLogger.GRAY}... ({len(lines)-20} more lines){VSCodeLogger.RESET}")

    @staticmethod
    def chatbot_response(text):
        lines = text.split('\n')
        for line in lines[:15]:
            if line.strip():
                print(f"{VSCodeLogger.WHITE}{line}{VSCodeLogger.RESET}")
        if len(lines) > 15:
            print(f"{VSCodeLogger.GRAY}... ({len(lines)-15} more lines){VSCodeLogger.RESET}")

    @staticmethod
    def config_box(provider, model, max_iter, timeout):
        print(f"{VSCodeLogger.GRAY}┌─ Configuration{VSCodeLogger.RESET}")
        print(f"{VSCodeLogger.GRAY}│  Provider: {VSCodeLogger.RESET}{provider}")
        print(f"{VSCodeLogger.GRAY}│  Model: {VSCodeLogger.RESET}{model}")
        print(f"{VSCodeLogger.GRAY}│  Max Iterations: {VSCodeLogger.RESET}{max_iter}")
        print(f"{VSCodeLogger.GRAY}│  Timeout: {VSCodeLogger.RESET}{timeout}s")
        print(f"{VSCodeLogger.GRAY}└─────────────────{VSCodeLogger.RESET}\n")

def load_test_cases():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")

    if not os.path.exists(config_path):
        config_path = "test_cases.json"

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_action(text: str):
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

def run_chatbot(query: str, provider) -> str:
    response = provider.generate(query, system_prompt=CHATBOT_BASELINE_PROMPT)
    return response

def run_agent(query: str, provider):
    conversation = f"User: {query}\n\n"
    step = 0

    while step < MAX_ITERATIONS:
        step += 1
        VSCodeLogger.step_start(step, MAX_ITERATIONS)

        full_prompt = REACT_SYSTEM_PROMPT + conversation
        if hasattr(provider, 'chat'):
            llm_output = provider.chat(query, conversation)
        else:
            llm_output = provider.generate(full_prompt)

        # Extract thought
        thought_match = re.search(r'Thought\s*:\s*(.*?)(?:Action\s*:|$)', llm_output, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()
            VSCodeLogger.thought(thought[:200])

        conversation += llm_output + "\n"

        # Check for final answer
        if "Final Answer:" in llm_output or "Câu trả lời cuối cùng:" in llm_output:
            final_match = re.search(r'(?:Final Answer|Câu trả lời cuối cùng)\s*:\s*(.*)', llm_output, re.DOTALL)
            if final_match:
                VSCodeLogger.final_answer_header()
                VSCodeLogger.final_answer(final_match.group(1).strip())
            return

        # Parse action
        tool_name, params = parse_action(llm_output)

        if not tool_name:
            VSCodeLogger.error("No valid Action format found")
            conversation += "System: Please use format 'Action: tool_name(param1, param2, ...)'\n\n"
            continue

        VSCodeLogger.action(tool_name, params)

        # Check tool exists
        if tool_name not in TOOL_REGISTRY:
            VSCodeLogger.error(f"Tool '{tool_name}' not found")
            conversation += f"Observation: Tool '{tool_name}' not found.\n\n"
            continue

        # Execute tool
        success, result = execute_tool(tool_name, params)
        VSCodeLogger.observation(result)

        conversation += f"Observation: {result}\n\n"

    VSCodeLogger.guardrail(f"Reached max iterations ({MAX_ITERATIONS}). Stopping loop.")

def display_menu():
    print(f"\n{VSCodeLogger.BOLD}Select Test Case:{VSCodeLogger.RESET}\n")
    tests = load_test_cases()
    for i, test in enumerate(tests, 1):
        category = test.get("category", "Unknown")
        question = test["question"]
        print(f"  {VSCodeLogger.BLUE}[{i}]{VSCodeLogger.RESET} {category}")
        print(f"      {question}\n")
    print(f"  {VSCodeLogger.BLUE}[0]{VSCodeLogger.RESET} Run all test cases")
    print(f"  {VSCodeLogger.BLUE}[c]{VSCodeLogger.RESET} Custom question")
    print(f"  {VSCodeLogger.BLUE}[q]{VSCodeLogger.RESET} Quit\n")

def interactive_demo(provider):
    display_menu()

    while True:
        choice = input(f"{VSCodeLogger.GRAY}❯{VSCodeLogger.RESET} ").strip().lower()

        if choice == 'q':
            print(f"\n{VSCodeLogger.GREEN}Goodbye!{VSCodeLogger.RESET}\n")
            break
        elif choice == '0':
            tests = load_test_cases()
            for idx, test in enumerate(tests):
                VSCodeLogger.header(f"Test Case {idx+1}: {test.get('category', 'Unknown')}")
                VSCodeLogger.section("Question", test["question"])

                print(f"\n{VSCodeLogger.BOLD}CHATBOT BASELINE{VSCodeLogger.RESET}")
                print(f"{VSCodeLogger.GRAY}{'─'*76}{VSCodeLogger.RESET}")
                chatbot_resp = run_chatbot(test["question"], provider)
                VSCodeLogger.chatbot_response(chatbot_resp)

                print(f"\n{VSCodeLogger.BOLD}REACT AGENT{VSCodeLogger.RESET}")
                print(f"{VSCodeLogger.GRAY}{'─'*76}{VSCodeLogger.RESET}")
                run_agent(test["question"], provider)

                print("\n")

        elif choice == 'c':
            custom_question = input(f"\n{VSCodeLogger.GRAY}Enter question:{VSCodeLogger.RESET} ").strip()
            if custom_question:
                VSCodeLogger.header("Custom Question")
                VSCodeLogger.section("Question", custom_question)

                print(f"\n{VSCodeLogger.BOLD}CHATBOT BASELINE{VSCodeLogger.RESET}")
                print(f"{VSCodeLogger.GRAY}{'─'*76}{VSCodeLogger.RESET}")
                chatbot_resp = run_chatbot(custom_question, provider)
                VSCodeLogger.chatbot_response(chatbot_resp)

                print(f"\n{VSCodeLogger.BOLD}REACT AGENT{VSCodeLogger.RESET}")
                print(f"{VSCodeLogger.GRAY}{'─'*76}{VSCodeLogger.RESET}")
                run_agent(custom_question, provider)
            else:
                print(f"{VSCodeLogger.RED}Question cannot be empty{VSCodeLogger.RESET}")
        else:
            try:
                idx = int(choice) - 1
                tests = load_test_cases()
                if 0 <= idx < len(tests):
                    test = tests[idx]
                    VSCodeLogger.header(f"Test Case {idx+1}: {test.get('category', 'Unknown')}")
                    VSCodeLogger.section("Question", test["question"])
                    VSCodeLogger.section("Expected", test.get("expected_behavior", "N/A"))

                    print(f"\n{VSCodeLogger.BOLD}CHATBOT BASELINE{VSCodeLogger.RESET}")
                    print(f"{VSCodeLogger.GRAY}{'─'*76}{VSCodeLogger.RESET}")
                    chatbot_resp = run_chatbot(test["question"], provider)
                    VSCodeLogger.chatbot_response(chatbot_resp)

                    print(f"\n{VSCodeLogger.BOLD}REACT AGENT{VSCodeLogger.RESET}")
                    print(f"{VSCodeLogger.GRAY}{'─'*76}{VSCodeLogger.RESET}")
                    run_agent(test["question"], provider)
                else:
                    print(f"{VSCodeLogger.RED}Invalid test case number{VSCodeLogger.RESET}")
            except ValueError:
                print(f"{VSCodeLogger.RED}Invalid input{VSCodeLogger.RESET}")

if __name__ == "__main__":
    VSCodeLogger.header("MOC 4: ReAct Agent Demo")

    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    provider_name = provider.__class__.__name__

    VSCodeLogger.config_box(provider_name, model_name, MAX_ITERATIONS, TIMEOUT_SECONDS)

    tests = load_test_cases()
    print(f"{VSCodeLogger.GRAY}Loaded {len(tests)} test cases{VSCodeLogger.RESET}\n")

    interactive_demo(provider)
