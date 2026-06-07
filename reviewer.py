import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
import re
import json

_model = None
_tokenizer = None
_is_llama_cpp = False

def get_model():
    global _model, _tokenizer, _is_llama_cpp
    if _model is not None:
        return _model, _tokenizer, _is_llama_cpp

    # Try llama-cpp-python first
    try:
        import llama_cpp
        from huggingface_hub import hf_hub_download
        print("Attempting to load model via llama-cpp-python...")
        try:
            model_path = hf_hub_download(
                repo_id="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
                filename="qwen2.5-coder-7b-instruct-q4_k_m.gguf"
            )
        except Exception as e:
            print(f"Could not download 7B GGUF: {e}. Trying 1.5B GGUF...")
            model_path = hf_hub_download(
                repo_id="Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF",
                filename="qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
            )
        
        _model = llama_cpp.Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=4,
            verbose=False
        )
        _is_llama_cpp = True
        print("Successfully loaded model via llama-cpp-python")
        return _model, None, _is_llama_cpp
    except Exception as e:
        print(f"llama-cpp-python load failed: {e}. Falling back to transformers...")

    # Try transformers fallback
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = "Qwen/Qwen2.5-Coder-7B-Instruct"
        
        # On CPU, download the lighter 1.5B model to prevent memory issues and huge lag
        if device == "cpu":
            print("CPU-only detected. Using 1.5B model to prevent memory issues.")
            model_name = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
            
        print(f"Loading {model_name} via transformers on device: {device}...")
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        kwargs = {}
        if device == "cuda":
            kwargs["torch_dtype"] = torch.float16
            kwargs["device_map"] = "auto"
        else:
            kwargs["torch_dtype"] = torch.float32
            kwargs["device_map"] = "cpu"
            kwargs["low_cpu_mem_usage"] = True
            
        _model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)
        _is_llama_cpp = False
        print(f"Successfully loaded {model_name} via transformers")
        return _model, _tokenizer, _is_llama_cpp
    except Exception as ex:
        print(f"transformers load failed: {ex}")

    # Final fallback - mock
    print("WARNING: All LLM loading methods failed. Using mock rule-based reviewer.")
    _model = "mock"
    _is_llama_cpp = False
    return _model, None, _is_llama_cpp

def extract_json(text: str) -> dict:
    try:
        return json.loads(text.strip())
    except:
        pass
    
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except:
            pass
            
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end+1]
        try:
            return json.loads(candidate.strip())
        except:
            pass
            
    return {
        "slop_score": 5,
        "issues": [
            {
                "severity": "WARNING",
                "title": "JSON Parse Error",
                "description": f"Failed to parse model response as JSON. Raw: {text[:200]}"
            }
        ],
        "verdict": "Model returned invalid JSON format."
    }

def mock_review(code_text: str) -> dict:
    issues = []
    slop_score = 1
    
    chatgpt_patterns = [
        (r"(?i)// here is the (updated|correct) code", "ChatGPT Header Comment", "Conversational marker typical of AI model output code blocks."),
        (r"(?i)# here is the (updated|correct) code", "ChatGPT Header Comment", "Conversational marker typical of AI model output code blocks."),
        (r"(?i)// hope this helps", "Conversational Sign-off", "AI polite sign-off comment left in code."),
        (r"(?i)// feel free to adjust", "AI Suggestion Comment", "Generic placeholder comment common in LLM outputs."),
        (r"(?i)let's break down", "Explaining Comment", "AI conversational narration inside code block.")
    ]
    
    for pattern, title, desc in chatgpt_patterns:
        if re.search(pattern, code_text):
            issues.append({"severity": "CRITICAL", "title": title, "description": desc})
            slop_score = max(slop_score, 8)
            
    # Check for lazy TODOs
    if re.search(r"(?i)\bTODO\b.*(implement|fill|add|here)", code_text):
        issues.append({
            "severity": "WARNING",
            "title": "Lazy AI Placeholder TODO",
            "description": "Found a placeholder TODO comment. LLMs often leave core implementation details as exercise for the reader."
        })
        slop_score = max(slop_score, 5)
        
    # Check for empty except block
    if re.search(r"except\s*:\s*\n\s*pass", code_text) or re.search(r"except\s+Exception\s*:\s*\n\s*pass", code_text):
        issues.append({
            "severity": "CRITICAL",
            "title": "Silent Error Suppression",
            "description": "Detected 'except: pass' block. AI models frequently use silent exception catching to make code look functional."
        })
        slop_score = max(slop_score, 7)
        
    # Check for redundant utility functions
    if "def is_even" in code_text or "def calculate_sum" in code_text:
        issues.append({
            "severity": "INFO",
            "title": "Trivial Boilerplate Function",
            "description": "Includes trivial helper functions that are built into standard libraries or easily simplified."
        })
        slop_score = max(slop_score, 3)

    if not issues:
        issues.append({
            "severity": "INFO",
            "title": "No Obvious AI Patterns",
            "description": "Code does not show obvious conversational headers or classic silent error-handling traps."
        })
        verdict = "Looks like human-written code. Low slop indicators detected."
    else:
        verdict = f"AI Slop detected with score {slop_score}/10. Please address critical issues and clean placeholder comments."

    return {
        "slop_score": slop_score,
        "issues": issues,
        "verdict": verdict
    }

def review_code(code_text: str) -> dict:
    if not code_text.strip():
        return {
            "slop_score": 1,
            "issues": [{"severity": "INFO", "title": "Empty Code", "description": "No code provided to review."}],
            "verdict": "Provide some code to get a review."
        }
        
    model, tokenizer, is_llama_cpp = get_model()
    
    if model == "mock":
        return mock_review(code_text)
        
    system_prompt = (
        "You are a senior software engineer doing a code review. Your job is to detect AI-generated code problems.\n"
        "Be direct, specific, and critical. Do NOT say 'Great code!' or validate choices without evidence.\n"
        "Look for: hallucinated APIs, logical errors that look plausible, security vulnerabilities,\n"
        "unnecessary boilerplate, inconsistent naming, missing error handling, fake implementations.\n"
        "Output a JSON with keys: slop_score (int 1-10), issues (list of {severity, title, description}), verdict (str)."
    )
    
    raw_output = ""
    try:
        if is_llama_cpp:
            prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{code_text}<|im_end|>\n<|im_start|>assistant\n"
            res = model(
                prompt,
                max_tokens=1024,
                temperature=0.1,
                stop=["<|im_end|>", "<|endoftext|>"]
            )
            raw_output = res["choices"][0]["text"]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": code_text}
            ]
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            device = model.device
            inputs = tokenizer(prompt, return_tensors="pt").to(device)
            
            import torch
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=1024,
                    do_sample=False,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            input_len = inputs.input_ids.shape[1]
            generated_tokens = outputs[0][input_len:]
            raw_output = tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
        return extract_json(raw_output)
    except Exception as e:
        print(f"Inference error: {e}")
        return mock_review(code_text)
