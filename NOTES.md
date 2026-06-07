# Dev Blog: Building SloppyDiff — The AI Slop Detector

*Author: Autonomous Software Engineer*  
*Date: June 7, 2026*  
*Hackathon Track: Backyard AI (Build Small Hackathon)*

---

## The Core Philosophy: Fighting Sycophancy
With the explosion of LLMs, the volume of AI-generated code has skyrocketed. While code assistants speed up writing code, they have a major flaw: they are sycophantic. They rarely push back on design decisions, and they regularly introduce subtle, logical bugs that *look* correct at first glance. Even worse, they tend to over-engineer solutions, dump massive boilerplates, and sneak in conversational placeholders like `"// hope this helps!"` or lazy `except: pass` exception suppression. 

**SloppyDiff** was born out of frustration. I wanted a code reviewer that is brutally honest. A reviewer that doesn't say "Great job, but...", but instead highlights exactly where the code smells like AI slop.

---

## Technical Architecture & Overcoming Local Hardware Constraints
Building a Gradio application that is fully offline ("Off the Grid" badge) and capable of running in low-resource container environments (like Hugging Face Space basic CPU instances) required a multi-tiered loading strategy in `reviewer.py`.

### 1. The Multi-Tier Model Loader
Our system first attempts to import `llama-cpp-python` and download the quantized GGUF format of `Qwen/Qwen2.5-Coder-7B-Instruct`. Quantization is essential to run local models on consumer-grade hardware. 
However, since Hugging Face Space basic environments may lack appropriate compiler tools or GPU drivers, compiling `llama-cpp-python` often fails on deployment. Therefore, we built a dynamic fallback to standard `transformers`.
Under `transformers`, loading a 7B model on a CPU-only node runs extremely slowly and typically exceeds the 16GB RAM container limits, causing silent crashes. To address this, we detect the device type:
- If a GPU is present, we load the full `Qwen/Qwen2.5-Coder-7B-Instruct`.
- If CPU-only is detected, we automatically downgrade to the lighter `Qwen/Qwen2.5-Coder-1.5B-Instruct` model. This allows the app to load quickly and output answers under 10 seconds.
- If python libraries are completely missing or the environment is extremely constrained, we gracefully fall back to a custom rule-based keyword & regex detector. This ensures the app stays online and functional in any sandbox.

### 2. High-Fidelity GitHub PR Fetching
Rather than using heavy wrapper packages, `fetcher.py` directly fetches PR diffs using the unauthenticated GitHub API with the header `Accept: application/vnd.github.v3.diff`. This turns the JSON PR response directly into a raw diff string. In the event of API rate limits (which limit unauthenticated requests to 60/hour), the app falls back to fetching the direct `.diff` file redirect URL.

---

## Crafting a Terminal UI in Gradio
A standard web UI doesn't fit a hacky, raw developer tool. To give the app a premium feel, I loaded custom CSS to strip away Gradio's default layout styles. We established:
- A monospace font system (`Fira Code`).
- A dark Github-dark theme (`#0d1117` background) with green, amber, and red accents.
- Dynamic color-coded HTML badges for the Slop Score (green for human, amber for mild slop, glowing red for pure slop).

The result is a responsive, aesthetically rich, and brutally honest AI review dashboard that runs in any environment.
