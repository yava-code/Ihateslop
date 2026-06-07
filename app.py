import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import gradio as gr
import fetcher
import reviewer
import json

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
    gr.HTML("<div class='terminal-title'>SloppyDiff — AI Slop Detector</div>")
    gr.HTML("<div class='terminal-subtitle'>Detect AI-generated code, lazy patterns, and logical hallucinations</div>")
    
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

if __name__ == "__main__":
    demo.launch()
