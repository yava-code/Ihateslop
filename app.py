import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import gradio as gr
import fetcher
import reviewer
import json
import asyncio
import threading
import dotenv

# Load .env file
dotenv.load_dotenv()

# Background service runners
def start_fastapi_server():
    try:
        import uvicorn
        from magda_agent.api import app as fastapi_app
        print("[Magda Backend] Starting FastAPI server on port 8000...")
        uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")
    except Exception as e:
        print(f"[Magda Backend] Error starting FastAPI: {e}")

def start_telegram_bot():
    try:
        from magda_agent.main import main as bot_main
        print("[Magda Telegram] Starting Telegram Bot loop...")
        asyncio.run(bot_main())
    except Exception as e:
        print(f"[Magda Telegram] Error starting Telegram Bot: {e}")

# Callbacks for Magda AGI Agent Console
async def chat_with_magda(message):
    message = message.strip()
    if not message:
        return "Please type something...", "No trace available."
    try:
        from magda_agent.api import consciousness, thought_chain_tracer
        thought_chain_tracer.start_trace()
        reply = await consciousness.process_input(message, user_id=None)
        
        trace = thought_chain_tracer.get_trace()
        trace_lines = []
        for step in trace:
            trace_lines.append(f"[{step.get('step', 'Cognition')}] {step.get('description', '')}")
        trace_str = "\n".join(trace_lines) if trace_lines else "No thought chain recorded."
        
        return reply, trace_str
    except Exception as e:
        return f"Error: {e}", f"Trace error: {e}"

def get_magda_internal_state():
    try:
        from magda_agent.api import consciousness
        return consciousness.get_internal_state()
    except Exception as e:
        return f"Could not retrieve state: {e}"

async def get_magda_tasks_table():
    rows = []
    try:
        from magda_agent.api import task_store
        tasks = await task_store.list()
        for t in tasks:
            sumry = t.summary()
            rows.append([
                sumry.get("id", ""),
                sumry.get("status", ""),
                f"{sumry.get('iterations', 0)}/{sumry.get('max_iterations', 20)}",
                sumry.get("goal", "")
            ])
    except Exception as e:
        print(f"Error fetching autonomy tasks: {e}")
        
    try:
        manifest_path = "./agent_tasks.json"
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                tasks = data.get("tasks", [])
                for t in tasks:
                    if not any(row[0] == t.get("id") for row in rows):
                        rows.append([
                            t.get("id", ""),
                            t.get("status", ""),
                            "N/A",
                            t.get("title", "")
                        ])
    except Exception as e:
        print(f"Error fetching agent tasks: {e}")
        
    return rows

async def run_magda_task_action(task_id, action):
    task_id = task_id.strip()
    if not task_id:
        return "Error: Task ID required.", await get_magda_tasks_table()
    try:
        from magda_agent.api import task_store
        if action == "cancel":
            ok = await task_store.request_cancel(task_id)
        elif action == "pause":
            ok = await task_store.request_pause(task_id)
        elif action == "resume":
            ok = await task_store.resume(task_id)
        else:
            return "Error: Unknown action.", await get_magda_tasks_table()
        
        res = "Success" if ok else "Failed (Task not found or incompatible state)"
        return f"Action '{action}' on '{task_id}': {res}", await get_magda_tasks_table()
    except Exception as e:
        return f"Error running action: {e}", await get_magda_tasks_table()

async def create_magda_task(goal):
    goal = goal.strip()
    if not goal:
        return "Error: Goal required.", await get_magda_tasks_table()
    try:
        from magda_agent.api import task_store
        t = await task_store.add_task(goal, max_iterations=20)
        return f"Task created successfully. ID: {t.id}", await get_magda_tasks_table()
    except Exception as e:
        return f"Error creating task: {e}", await get_magda_tasks_table()

# Custom terminal CSS styling
css = """
body, html, .gradio-container {
    background-color: #0d1117 !important;
    color: #c9d1d9 !important;
    font-family: 'Fira Code', 'Courier New', Courier, monospace !important;
}

textarea, input, select, button, span, p, h1, h2, h3, h4 {
    font-family: 'Fira Code', 'Courier New', Courier, monospace !important;
}

textarea {
    background-color: #161b22 !important;
    color: #58a6ff !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
}

.terminal-title {
    text-align: center;
    color: #58a6ff;
    text-shadow: 0 0 10px rgba(88, 166, 255, 0.5);
    font-size: 2.2rem;
    margin-bottom: 0.1rem;
}

.terminal-subtitle {
    text-align: center;
    color: #8b949e;
    margin-bottom: 1.5rem;
    font-size: 1rem;
}

.terminal-panel {
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    background-color: #161b22 !important;
    padding: 1.2rem !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
}

button.primary-btn {
    background-color: #238636 !important;
    color: #ffffff !important;
    font-weight: bold !important;
    border: 1px solid #308f43 !important;
    border-radius: 6px !important;
    padding: 10px 20px !important;
    cursor: pointer !important;
    transition: all 0.2s ease-in-out !important;
}

button.primary-btn:hover {
    background-color: #2ea043 !important;
    box-shadow: 0 0 10px rgba(46, 160, 67, 0.5) !important;
}

.slop-badge {
    font-size: 3rem !important;
    font-weight: 800 !important;
    text-align: center !important;
    margin: 10px 0 !important;
}

.verdict-box {
    border-left: 4px solid #f0883e !important;
    background-color: #1f1f1d !important;
    padding: 12px !important;
    margin-top: 10px !important;
    border-radius: 4px;
}
"""

def get_score_badge(score_str):
    try:
        score = int(score_str.split('/')[0])
    except:
        score = 0
    
    if score >= 8:
        color = "#ff7b72"  # Red-orange
        glow = "rgba(255, 123, 114, 0.4)"
    elif score >= 5:
        color = "#d29922"  # Amber
        glow = "rgba(210, 153, 34, 0.4)"
    else:
        color = "#3fb950"  # Green
        glow = "rgba(63, 185, 80, 0.4)"
        
    return f'<div class="slop-badge" style="color: {color} !important; text-shadow: 0 0 10px {glow} !important;">{score_str}</div>'

def analyze(input_text):
    input_text = input_text.strip()
    if not input_text:
        badge_html = get_score_badge("0/10")
        return "Error: No input provided.", badge_html, "Please paste code or a public GitHub PR URL.", [], "{}"

    parsed = fetcher.parse_github_url(input_text)
    if parsed:
        owner, repo, number = parsed
        status_info = f"Fetching PR diff for {owner}/{repo} #{number}..."
        print(status_info)
        try:
            code_to_review = fetcher.fetch_pr_diff(owner, repo, number)
            source_label = f"GitHub PR: {owner}/{repo} #{number}"
        except Exception as e:
            badge_html = get_score_badge("0/10")
            return f"Error fetching PR: {str(e)}", badge_html, "Could not fetch PR diff.", [], "{}"
    else:
        code_to_review = input_text
        source_label = "Pasted Snippet"

    print(f"Running review on {source_label}...")
    try:
        review = reviewer.review_code(code_to_review)
    except Exception as e:
        badge_html = get_score_badge("0/10")
        return f"Review error: {str(e)}", badge_html, "Model execution failed.", [], "{}"

    slop_score = review.get("slop_score", 5)
    verdict = review.get("verdict", "No verdict provided.")
    issues = review.get("issues", [])

    formatted_issues = []
    for issue in issues:
        sev = issue.get("severity", "INFO").upper()
        title = issue.get("title", "Unknown issue")
        desc = issue.get("description", "")
        formatted_issues.append([sev, title, desc])

    status_info = f"Analyzed {source_label} successfully ({len(code_to_review)} chars)."
    badge_html = get_score_badge(f"{slop_score}/10")
    
    return status_info, badge_html, verdict, formatted_issues, json.dumps(review, indent=2)

with gr.Blocks(css=css, theme=gr.themes.Default()) as demo:
    gr.HTML("<div class='terminal-title'>SloppyDiff — AI Slop Detector & AGI Console</div>")
    gr.HTML("<div class='terminal-subtitle'>Analyze code slop or interact with the Magda cognitive architecture</div>")
    
    with gr.Tabs():
        with gr.Tab("SloppyDiff Code Reviewer"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML("<h3>[INPUT CONFIGURATION]</h3>")
                    input_box = gr.Textbox(
                        label="Code Snippet or GitHub PR URL",
                        placeholder="Paste code or a PR URL (e.g. https://github.com/owner/repo/pull/123)",
                        lines=12,
                        max_lines=30
                    )
                    submit_btn = gr.Button("RUN DETECTOR", elem_classes=["primary-btn"])
                    
                    gr.Examples(
                        examples=[
                            [
                                "// ChatGPT generated code helper\n"
                                "// Here is the implementation of the requested average calculation\n"
                                "def calculate_average(numbers):\n"
                                "    try:\n"
                                "        # TODO: check for division by zero\n"
                                "        return sum(numbers) / len(numbers)\n"
                                "    except Exception:\n"
                                "        # hope this helps!\n"
                                "        pass"
                            ],
                            ["https://github.com/psf/requests/pull/6262"],
                            [
                                "# Human-written binary search\n"
                                "def binary_search(arr, target):\n"
                                "    low, high = 0, len(arr) - 1\n"
                                "    while low <= high:\n"
                                "        mid = (low + high) // 2\n"
                                "        if arr[mid] == target:\n"
                                "            return mid\n"
                                "        elif arr[mid] < target:\n"
                                "            low = mid + 1\n"
                                "        else:\n"
                                "            high = mid - 1\n"
                                "    return -1"
                            ]
                        ],
                        inputs=input_box,
                        label="Try Examples"
                    )
                    
                with gr.Column(scale=1):
                    gr.HTML("<h3>[DETECTION RESULTS]</h3>")
                    
                    with gr.Group(elem_classes=["terminal-panel"]):
                        status_text = gr.Textbox(label="Status Console", value="System Idle. Awaiting input...", interactive=False)
                        
                        gr.HTML("<div style='text-align:center; margin-top:10px;'><strong>SLOP LEVEL</strong></div>")
                        score_badge = gr.HTML(value=get_score_badge("0/10"))
                        
                        verdict_text = gr.Textbox(
                            label="Summary Verdict",
                            placeholder="Verdict details will appear here...",
                            interactive=False
                        )
                        
                        issues_table = gr.Dataframe(
                            headers=["Severity", "Issue Category", "Details"],
                            datatype=["str", "str", "str"],
                            col_count=(3, "fixed"),
                            interactive=False,
                            label="Detected Issues / Patterns"
                        )
                        
                        with gr.Accordion("Raw Response JSON", open=False):
                            raw_json = gr.Code(label="JSON Payload", language="json", interactive=False)

            submit_btn.click(
                fn=analyze,
                inputs=input_box,
                outputs=[status_text, score_badge, verdict_text, issues_table, raw_json]
            )

        with gr.Tab("Magda AGI Agent"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML("<h3>[AGENT CHAT]</h3>")
                    chat_input = gr.Textbox(
                        label="Your message to Magda",
                        placeholder="Hello Magda, how is your PAD state?",
                        lines=3
                    )
                    chat_submit_btn = gr.Button("SEND TO MAGDA", elem_classes=["primary-btn"])
                    chat_output = gr.Textbox(
                        label="Magda's Response",
                        interactive=False,
                        lines=10
                    )
                    
                with gr.Column(scale=1):
                    gr.HTML("<h3>[COGNITIVE STATE & REASONING]</h3>")
                    with gr.Group(elem_classes=["terminal-panel"]):
                        state_btn = gr.Button("REFRESH INTERNAL STATE")
                        state_display = gr.Textbox(
                            label="Magda Internal Mind State (Emotional Engine / Context)",
                            interactive=False,
                            lines=6
                        )
                        thought_display = gr.Textbox(
                            label="Thought Chain Trace (Reasoning Steps)",
                            interactive=False,
                            lines=10
                        )
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML("<h3>[AUTONOMOUS GOALS / TASK MANAGER]</h3>")
                    new_task_input = gr.Textbox(
                        label="Define New Goal / Task",
                        placeholder="e.g. check codebase for open issues or test coverage"
                    )
                    create_task_btn = gr.Button("QUEUE TASK")
                    task_status_msg = gr.Textbox(label="Operation Result", interactive=False)

                with gr.Column(scale=1):
                    gr.HTML("<h3>[ACTIVE TASK LIST]</h3>")
                    with gr.Group(elem_classes=["terminal-panel"]):
                        tasks_list_btn = gr.Button("REFRESH TASK LIST")
                        tasks_display_table = gr.Dataframe(
                            headers=["Task ID", "Status", "Iterations", "Goal"],
                            datatype=["str", "str", "str", "str"],
                            col_count=(4, "fixed"),
                            interactive=False,
                            label="Active Tasks Manifest"
                        )
                        
                        with gr.Row():
                            control_task_id = gr.Textbox(
                                label="Target Task ID",
                                placeholder="e.g. architecture-contracts"
                            )
                            control_action = gr.Dropdown(
                                choices=["cancel", "pause", "resume"],
                                label="Action"
                            )
                        control_btn = gr.Button("EXECUTE ACTION")

            # Click Handlers for Magda Tab
            chat_submit_btn.click(
                fn=chat_with_magda,
                inputs=chat_input,
                outputs=[chat_output, thought_display]
            )
            
            state_btn.click(
                fn=get_magda_internal_state,
                outputs=state_display
            )
            
            tasks_list_btn.click(
                fn=get_magda_tasks_table,
                outputs=tasks_display_table
            )
            
            create_task_btn.click(
                fn=create_magda_task,
                inputs=new_task_input,
                outputs=[task_status_msg, tasks_display_table]
            )
            
            control_btn.click(
                fn=run_magda_task_action,
                inputs=[control_task_id, control_action],
                outputs=[task_status_msg, tasks_display_table]
            )

if __name__ == "__main__":
    # Start FastAPI server in background
    api_token = os.getenv("MAGDA_API_TOKEN")
    if api_token:
        t_api = threading.Thread(target=start_fastapi_server, daemon=True)
        t_api.start()
        print("[Startup] FastAPI backend thread launched.")
    else:
        print("[Startup] MAGDA_API_TOKEN not set. Skipping background FastAPI server.")
        
    # Start Telegram bot in background
    bot_token = os.getenv("BOT_TOKEN")
    if bot_token and bot_token != "dummy_token":
        t_bot = threading.Thread(target=start_telegram_bot, daemon=True)
        t_bot.start()
        print("[Startup] Telegram bot thread launched.")
    else:
        print("[Startup] Telegram BOT_TOKEN is empty/dummy. Skipping Telegram bot launch.")
        
    demo.launch()
