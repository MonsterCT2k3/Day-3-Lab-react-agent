"""
MOC 4: WEB UI DEMO - Flask Application
Professional web interface for presentation and demo
Font size: Large and clear for projection
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

# Try to import Flask, if not available, provide instructions
try:
    from flask import Flask, render_template_string, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Flask not installed. Run: pip install flask")

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

def run_chatbot(query: str, provider) -> str:
    """Run chatbot and return response"""
    response = provider.generate(query, system_prompt=CHATBOT_BASELINE_PROMPT)
    return response

def run_agent(query: str, provider) -> dict:
    """Run ReAct Agent and return detailed log"""
    log = {
        "steps": [],
        "final_answer": None,
        "total_steps": 0,
        "guardrail_triggered": False
    }

    conversation = f"User: {query}\n\n"
    step = 0

    while step < MAX_ITERATIONS:
        step += 1
        log["total_steps"] = step
        step_log = {"step": step, "thought": None, "action": None, "observation": None, "error": None}

        full_prompt = REACT_SYSTEM_PROMPT + conversation
        if hasattr(provider, 'chat'):
            llm_output = provider.chat(query, conversation)
        else:
            llm_output = provider.generate(full_prompt)

        # Extract thought
        thought_match = re.search(r'Thought\s*:\s*(.*?)(?:Action\s*:|$)', llm_output, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip().split('\n')[0][:200]
            step_log["thought"] = thought

        conversation += llm_output + "\n"

        # Check for final answer
        if "Final Answer:" in llm_output or "Câu trả lời cuối cùng:" in llm_output:
            final_match = re.search(r'(?:Final Answer|Câu trả lời cuối cùng)\s*:\s*(.*)', llm_output, re.DOTALL)
            if final_match:
                log["final_answer"] = final_match.group(1).strip()
            log["steps"].append(step_log)
            return log

        # Parse action
        tool_name, params = parse_action(llm_output)

        if not tool_name:
            step_log["error"] = "No valid Action format found"
            conversation += "System: Please use format 'Action: tool_name(param1, param2, ...)'\n\n"
            log["steps"].append(step_log)
            continue

        step_log["action"] = {"tool": tool_name, "params": params}

        # Check tool exists
        if tool_name not in TOOL_REGISTRY:
            step_log["error"] = f"Tool '{tool_name}' not found"
            conversation += f"Observation: Tool '{tool_name}' not found.\n\n"
            log["steps"].append(step_log)
            continue

        # Execute tool
        success, result = execute_tool(tool_name, params)
        step_log["observation"] = result
        conversation += f"Observation: {result}\n\n"

        log["steps"].append(step_log)

    log["guardrail_triggered"] = True
    log["final_answer"] = "Max iterations reached. Stopping loop."
    return log

# ============================================================================
# FLASK APP
# ============================================================================

app = Flask(__name__)
provider = get_llm_provider()

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MOC 4: ReAct Agent Demo</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            background: #2c3e50;
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            text-align: center;
        }

        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        header p {
            font-size: 1.3em;
            opacity: 0.9;
        }

        .config-box {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .config-box h3 {
            font-size: 1.4em;
            margin-bottom: 15px;
            color: #2c3e50;
        }

        .config-item {
            display: inline-block;
            margin-right: 30px;
            font-size: 1.1em;
            margin-bottom: 10px;
        }

        .config-label {
            font-weight: bold;
            color: #2c3e50;
        }

        .test-cases {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }

        .test-case-card {
            background: white;
            padding: 25px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 5px solid #3498db;
        }

        .test-case-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            background: #f9f9f9;
        }

        .test-case-card.active {
            background: #ecf0f1;
            border-left-color: #27ae60;
        }

        .test-case-category {
            font-size: 0.95em;
            color: #7f8c8d;
            margin-bottom: 10px;
            font-weight: 600;
        }

        .test-case-question {
            font-size: 1.25em;
            color: #2c3e50;
            margin-bottom: 15px;
            font-weight: 500;
        }

        .test-case-behavior {
            font-size: 1em;
            color: #555;
            font-style: italic;
        }

        .demo-section {
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .demo-section h3 {
            font-size: 1.6em;
            margin-bottom: 20px;
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }

        .demo-content {
            font-size: 1.15em;
            line-height: 1.8;
            color: #333;
        }

        .step {
            margin: 20px 0;
            padding: 20px;
            background: #ecf0f1;
            border-left: 4px solid #3498db;
            border-radius: 4px;
        }

        .step-header {
            font-weight: bold;
            font-size: 1.15em;
            color: #2c3e50;
            margin-bottom: 10px;
        }

        .step-thought {
            color: #7f8c8d;
            margin: 10px 0;
            font-style: italic;
        }

        .step-action {
            background: #e8f4f8;
            padding: 15px;
            border-radius: 4px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 1em;
            margin: 10px 0;
            color: #c0392b;
        }

        .step-observation {
            background: #f4f4f4;
            padding: 15px;
            border-radius: 4px;
            font-size: 1em;
            margin: 10px 0;
            color: #27ae60;
        }

        .step-error {
            background: #fadbd8;
            color: #c0392b;
            padding: 15px;
            border-radius: 4px;
            margin: 10px 0;
        }

        .final-answer {
            background: #d5f4e6;
            border-left: 4px solid #27ae60;
            padding: 25px;
            border-radius: 4px;
            margin-top: 20px;
            font-size: 1.15em;
            color: #27ae60;
        }

        .guardrail-notice {
            background: #fdeaa8;
            border-left: 4px solid #f39c12;
            padding: 15px;
            border-radius: 4px;
            margin-top: 10px;
            font-size: 1.1em;
            color: #d68910;
        }

        .loading {
            text-align: center;
            padding: 30px;
            font-size: 1.3em;
            color: #7f8c8d;
        }

        .custom-input-section {
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .custom-input-section h3 {
            font-size: 1.6em;
            margin-bottom: 20px;
            color: #2c3e50;
        }

        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }

        input[type="text"] {
            flex: 1;
            padding: 15px;
            font-size: 1.1em;
            border: 2px solid #bdc3c7;
            border-radius: 4px;
            font-family: inherit;
        }

        input[type="text"]:focus {
            outline: none;
            border-color: #3498db;
            box-shadow: 0 0 5px rgba(52, 152, 219, 0.3);
        }

        button {
            padding: 15px 30px;
            font-size: 1.15em;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.3s ease;
        }

        button:hover {
            background: #2980b9;
        }

        button:active {
            transform: scale(0.98);
        }

        @media (max-width: 1024px) {
            .test-cases {
                grid-template-columns: 1fr;
            }

            header h1 {
                font-size: 2em;
            }

            .demo-section h3 {
                font-size: 1.4em;
            }

            .demo-content {
                font-size: 1.05em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>MOC 4: ReAct Agent Demo</h1>
            <p>Professional Demonstration & Cross Audit</p>
        </header>

        <div class="config-box">
            <h3>Configuration</h3>
            <div class="config-item">
                <span class="config-label">LLM Provider:</span> {{ provider }}
            </div>
            <div class="config-item">
                <span class="config-label">Model:</span> {{ model }}
            </div>
            <div class="config-item">
                <span class="config-label">Max Iterations:</span> {{ max_iterations }}
            </div>
            <div class="config-item">
                <span class="config-label">Timeout:</span> {{ timeout }}s
            </div>
        </div>

        <div class="custom-input-section">
            <h3>Custom Question</h3>
            <div class="input-group">
                <input type="text" id="customQuestion" placeholder="Enter your custom question here..." />
                <button onclick="runCustomDemo()">Run Demo</button>
            </div>
        </div>

        <div>
            <h2 style="font-size: 1.8em; margin-bottom: 20px; color: #2c3e50;">Test Cases</h2>
            <div class="test-cases" id="testCases"></div>
        </div>

        <div id="demoOutput"></div>
    </div>

    <script>
        const testCases = {{ test_cases | tojson }};

        function initTestCases() {
            const container = document.getElementById('testCases');
            testCases.forEach((test, index) => {
                const card = document.createElement('div');
                card.className = 'test-case-card';
                card.innerHTML = `
                    <div class="test-case-category">${test.category}</div>
                    <div class="test-case-question">${test.question}</div>
                    <div class="test-case-behavior"><strong>Expected:</strong> ${test.expected_behavior}</div>
                `;
                card.onclick = () => runDemo(index);
                container.appendChild(card);
            });
        }

        function runDemo(testIndex) {
            const demoOutput = document.getElementById('demoOutput');
            demoOutput.innerHTML = '<div class="loading">Running demo...</div>';

            fetch('/run_demo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ test_index: testIndex })
            })
            .then(res => res.json())
            .then(data => displayDemo(data))
            .catch(err => {
                demoOutput.innerHTML = '<div class="loading">Error: ' + err.message + '</div>';
            });
        }

        function runCustomDemo() {
            const question = document.getElementById('customQuestion').value.trim();
            if (!question) {
                alert('Please enter a question');
                return;
            }

            const demoOutput = document.getElementById('demoOutput');
            demoOutput.innerHTML = '<div class="loading">Running demo...</div>';

            fetch('/run_demo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ custom_question: question })
            })
            .then(res => res.json())
            .then(data => displayDemo(data))
            .catch(err => {
                demoOutput.innerHTML = '<div class="loading">Error: ' + err.message + '</div>';
            });
        }

        function displayDemo(data) {
            let html = '<div id="demoOutput">';

            // Chatbot section
            html += '<div class="demo-section">';
            html += '<h3>Chatbot Baseline Response</h3>';
            html += '<div class="demo-content">' + escapeHtml(data.chatbot_response) + '</div>';
            html += '</div>';

            // Agent section
            html += '<div class="demo-section">';
            html += '<h3>ReAct Agent Response</h3>';

            data.agent_log.steps.forEach((step, idx) => {
                html += '<div class="step">';
                html += '<div class="step-header">Step ' + step.step + '</div>';

                if (step.thought) {
                    html += '<div class="step-thought">💭 ' + escapeHtml(step.thought) + '</div>';
                }

                if (step.action) {
                    html += '<div class="step-action">⚙️ ACTION: ' + step.action.tool + '(' + step.action.params.join(', ') + ')</div>';
                }

                if (step.observation) {
                    html += '<div class="step-observation">👁️ OBSERVATION: ' + escapeHtml(step.observation.substring(0, 200)) + (step.observation.length > 200 ? '...' : '') + '</div>';
                }

                if (step.error) {
                    html += '<div class="step-error">❌ ERROR: ' + escapeHtml(step.error) + '</div>';
                }

                html += '</div>';
            });

            if (data.agent_log.final_answer) {
                html += '<div class="final-answer">✓ FINAL ANSWER: ' + escapeHtml(data.agent_log.final_answer) + '</div>';
            }

            if (data.agent_log.guardrail_triggered) {
                html += '<div class="guardrail-notice">⚠️ GUARDRAIL: Max iterations reached</div>';
            }

            html += '</div>';
            html += '</div>';

            document.getElementById('demoOutput').innerHTML = html;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        initTestCases();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    tests = load_test_cases()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    provider_name = provider.__class__.__name__

    return render_template_string(HTML_TEMPLATE,
        test_cases=tests,
        provider=provider_name,
        model=model_name,
        max_iterations=MAX_ITERATIONS,
        timeout=TIMEOUT_SECONDS
    )

@app.route('/run_demo', methods=['POST'])
def run_demo():
    data = request.json
    tests = load_test_cases()

    if 'test_index' in data:
        test = tests[data['test_index']]
        question = test['question']
    else:
        question = data.get('custom_question', '')

    # Run both chatbot and agent
    chatbot_response = run_chatbot(question, provider)
    agent_log = run_agent(question, provider)

    return jsonify({
        'question': question,
        'chatbot_response': chatbot_response,
        'agent_log': agent_log
    })

if __name__ == '__main__':
    if not FLASK_AVAILABLE:
        print("Flask is required to run this web demo.")
        print("Install it with: pip install flask")
        sys.exit(1)

    print("\n" + "="*70)
    print("MOC 4: Web Demo Starting".center(70))
    print("="*70)
    print("\nOpen your browser and go to: http://localhost:5000")
    print("Press Ctrl+C to stop the server\n")

    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)
