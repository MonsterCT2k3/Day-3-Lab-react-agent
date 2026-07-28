"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer)
File chính ghép nối tất cả các thành phần: Tools + Prompts + Test Cases + Multi-Provider.
"""

import json
import os
import sys
from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import các thành phần từ file của Role 2, Role 3 & Multi-Provider Adapter
from tools import TOOL_REGISTRY
from prompts import CHATBOT_BASELINE_PROMPT, REACT_SYSTEM_PROMPT, MAX_ITERATIONS, TIMEOUT_SECONDS
from providers import get_llm_provider
import re
import time

load_dotenv()

def load_test_cases():
    """Đọc bộ test cases từ config/test_cases.json của Role 1"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    
    # Fallback kiểm tra nếu file ở thư mục hiện tại
    if not os.path.exists(config_path):
        config_path = "test_cases.json"
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_baseline_chatbot(user_query: str, provider):
    """
    Dựng Chatbot gốc (Baseline) không có công cụ.
    """
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    print(f"⚙️ System Prompt: {CHATBOT_BASELINE_PROMPT.strip()}")
    
    # Gọi LLM Provider thực hiện sinh câu trả lời
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot trả lời:\n{response}")

def parse_action(text: str):
    """
    Phân tích Action từ đầu ra LLM.
    Hỗ trợ cả 2 format: Action: tool_name(param1, param2, ...) hoặc Action: tool_name[param1, param2, ...]
    Trả về: (tool_name, [params]) hoặc (None, []) nếu không tìm thấy.
    """
    # Thử format với ngoặc tròn trước
    match = re.search(r'Action:\s*(\w+)\s*\((.*?)\)', text, re.DOTALL)
    if match:
        tool_name = match.group(1).strip()
        params_str = match.group(2).strip()
        params = []
        if params_str:
            params = [p.strip().strip('"\'') for p in params_str.split(',')]
        return tool_name, params

    # Thử format với ngoặc vuông
    match = re.search(r'Action:\s*(\w+)\s*\[(.*?)\]', text, re.DOTALL)
    if match:
        tool_name = match.group(1).strip()
        params_str = match.group(2).strip()
        params = []
        if params_str:
            params = [p.strip().strip('"\'') for p in params_str.split(',')]
        return tool_name, params

    return None, []


def execute_tool(tool_name: str, params: list):
    """
    Thực thi công cụ từ TOOL_REGISTRY.
    Trả về kết quả dưới dạng chuỗi.
    """
    if tool_name not in TOOL_REGISTRY:
        return f"❌ Error: Công cụ '{tool_name}' không tồn tại trong hệ thống."

    tool_func = TOOL_REGISTRY[tool_name]
    try:
        # Gọi tool với các tham số
        start_time = time.time()
        result = tool_func(*params) if params else tool_func()
        elapsed = time.time() - start_time

        if elapsed > TIMEOUT_SECONDS:
            return f"⏱️ Timeout: Công cụ {tool_name} vượt quá {TIMEOUT_SECONDS}s"

        return str(result)
    except Exception as e:
        return f"❌ Error khi thực thi {tool_name}: {str(e)}"


def run_baseline_test_cases(test_cases, provider, limit=10):
    """Chạy Chatbot baseline trên test case đầu tiên."""
    print(f"\n--- DEMO 1: CHẠY TRÊN {min(limit, len(test_cases))} TEST CASES CHATBOT BASELINE ---")
    for idx, test_case in enumerate(test_cases[:limit], start=1):
        print(f"\n=== Test case {idx}/{min(limit, len(test_cases))} ===")
        print(f"📌 Câu hỏi: {test_case['question']}")
        print(f"🧾 Category: {test_case.get('category', 'N/A')}")
        run_baseline_chatbot(test_case["question"], provider)


def run_react_agent(user_query: str, provider):
    """
    Dựng vòng lặp ReAct Agent (Thought -> Action -> Observation) có Guardrails.
    Tương tác với LLM thực tế để sinh Thought & Action, sau đó execute tool.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    print(f"⚙️ Guardrails: MAX_ITERATIONS={MAX_ITERATIONS}, TIMEOUT_SECONDS={TIMEOUT_SECONDS}\n")

    # Khởi tạo conversation history cho ReAct loop
    conversation = f"Người dùng: {user_query}\n\n"
    step = 0

    while step < MAX_ITERATIONS:
        step += 1
        print(f"\n{'='*60}")
        print(f"🔄 Bước {step}/{MAX_ITERATIONS}")
        print(f"{'='*60}")

        # Gọi LLM để sinh Thought & Action
        full_prompt = REACT_SYSTEM_PROMPT + conversation

        # Sử dụng provider.generate hoặc provider.chat nếu có conversation history
        if hasattr(provider, 'chat'):
            llm_output = provider.chat(user_query, conversation)
        else:
            llm_output = provider.generate(full_prompt)

        print(f"🤖 LLM Output:\n{llm_output}\n")
        conversation += llm_output + "\n"

        # Kiểm tra nếu LLM đã quyết định Final Answer
        if "Final Answer:" in llm_output or "Câu trả lời cuối cùng:" in llm_output:
            print(f"✅ Agent đã kết thúc với Final Answer")
            break

        # Phân tích Action từ LLM output
        tool_name, params = parse_action(llm_output)

        if not tool_name:
            print(f"⚠️ Không tìm thấy Action hợp lệ, yêu cầu LLM tiếp tục...")
            # Thêm instruction để LLM sinh Action
            conversation += "Hệ thống: Vui lòng sinh Action dưới dạng 'Action: tool_name(param1, param2, ...)'\n\n"
            continue

        # Kiểm tra tool có tồn tại không
        if tool_name not in TOOL_REGISTRY:
            print(f"❌ Tool '{tool_name}' không tồn tại. Các tool có sẵn: {list(TOOL_REGISTRY.keys())}")
            conversation += f"Observation: Tool '{tool_name}' không tồn tại trong hệ thống.\n\n"
            continue

        # Thực thi tool
        print(f"🛠️ Thực thi: {tool_name}({', '.join(params)})")
        observation = execute_tool(tool_name, params)
        print(f"👁️ Observation:\n{observation}\n")

        # Thêm Observation vào conversation
        conversation += f"Observation: {observation}\n\n"

    if step >= MAX_ITERATIONS:
        print(f"\n🛡️ GUARDRAIL TRIGGERED: Đã đạt {MAX_ITERATIONS} bước. Ngắt lặp an toàn!")


if __name__ == "__main__":
    print("==================================================")
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("==================================================")
    
    # Khởi tạo Multi-Provider LLM Adapter (Đọc từ biến môi trường LLM_PROVIDER)
    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} (Model: {model_name})")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases từ config/test_cases.json\n")

    # Chạy 5 câu test baseline
    run_baseline_test_cases(tests, provider, limit=5)

    # Chạy vòng lặp ReAct Agent với câu test số 3
    sample_query = tests[2]["question"]
    
    # print("--- DEMO 1: CHẠY TRÊN CHATBOT BASELINE ---")
    # run_baseline_chatbot(sample_query, provider)
    
    print("\n--- DEMO 2: CHẠY TRÊN REACT AGENT ---")
    run_react_agent(sample_query, provider)
