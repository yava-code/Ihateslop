---
title: SloppyDiff — AI Slop Detector
emoji: 🤖
colorFrom: red
colorTo: blue
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
pinned: false
tags:
- build-small-hackathon
- backyard-ai
---

# SloppyDiff — AI Slop Detector

SloppyDiff is a brutally honest, non-sycophantic code reviewer tailored to spot AI-generated code patterns ("slop") and logical code smells.

This project is built for the **Backyard AI** track of the **Build Small Hackathon** (huggingface.co/build-small-hackathon).

## Features
- **Snippets & PRs:** Paste direct snippets or fetch a public GitHub PR diff automatically.
- **Offline / Local Inference:** Runs entirely locally using `llama-cpp-python` with automatic fallback to `transformers`.
- **Slop Score:** 1-10 rating on the code's "slop" level.
- **Brutally Honest Reviews:** Designed to find logical contradictions, fake APIs, redundant boilerplate, and security issues.
# Ihateslop
