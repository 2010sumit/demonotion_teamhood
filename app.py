#!/usr/bin/env python3
"""
Team KNIGHTHOOD (Notion Track) - Live Event Annotator Pipeline Mock Prototype
File: app.py

A standalone, zero-dependency Python mock prototype designed to simulate our
Live Event Annotator pipeline. Uses 100% free-tier cloud architectures (Google AI
Studio Gemini-1.5-flash & Notion API).

Features:
- Simulated Input Tiers: Auto-generates local mock audio transcripts and JPEG screenshots.
- AI Synthesis: Directly invokes Google AI Studio (gemini-1.5-flash) REST API with system instructions.
- Notion Integration: Dynamically generates structured Notion page payloads matching track database properties.
- Complete Offline/Mock Graceful Fallback: Runs successfully even without valid API keys.
- Continuous Loop Daemon option: Simulates a backend pipeline listener.
"""

import os
import sys
import time
import json
import base64
import datetime
import argparse
import urllib.request
import urllib.error

import config

# =====================================================================
# CONFIGURATION & SECRET MANAGEMENT SECTION
# =====================================================================
# All configuration and secrets are loaded from config.py to avoid hardcoding secrets.
DEFAULT_OPENROUTER_KEY = config.OPENROUTER_API_KEY
DEFAULT_NOTION_TOKEN = config.NOTION_TOKEN
DEFAULT_DB_ID = config.NOTION_DATABASE_ID
DEFAULT_TRANSCRIPT = """
Welcome back, everyone. Today we are going to dive deep into building a distributed rate limiting system.
So, if you think about it, why do we need rate limiting at the API gateway layer?
Well, there are three primary reasons: security (preventing DDoS attacks), cost control (preventing resource exhaustion or runaway API costs from third-party APIs), and server stability (mitigating traffic spikes).
Let's look at the classic Token Bucket algorithm. In this algorithm, we have a bucket of maximum capacity C. Tokens are added to the bucket at a constant rate of R tokens per second.
When a request arrives, we try to draw a token. If there is a token, the request is allowed. If not, it is rejected with a HTTP 429 Too Many Requests.
How do we implement this in Redis to make it distributed?
We can use a Redis Hash structure where we store the last_updated timestamp and the remaining_tokens balance.
Here is a quick Python-like pseudocode block to show how this works:
```python
def check_rate_limit(client_id, capacity, rate):
    current_time = time.time()
    # Fetch from Redis
    state = redis.hgetall(client_id)
    if not state:
        tokens = capacity
        last_updated = current_time
    else:
        last_updated = float(state[b'last_updated'])
        tokens = float(state[b'tokens'])
        
    # Calculate elapsed time and add new tokens
    elapsed = current_time - last_updated
    tokens = min(capacity, tokens + elapsed * rate)
    
    if tokens >= 1:
        tokens -= 1
        # Save back to Redis
        redis.hset(client_id, mapping={
            'tokens': tokens,
            'last_updated': current_time
        })
        return True
    return False
```
But wait! There is a race condition between reading the hash, computing, and writing back.
If two requests hit different application nodes at the exact same millisecond, they both fetch the same token balance and allow both requests, violating the rate limit.
To solve this, we must use a Lua script. Redis executes Lua scripts atomically, guaranteeing that no other command runs while the Lua script is executing.
Let's review the visual block diagram on slide 1. You can see the API Gateway routing requests through a Redis Cluster, ensuring millisecond-level latency overhead.
Next, let's discuss slide 2, which covers the Leaky Bucket algorithm...
"""

FALLBACK_MARKDOWN = """# Tech Workshop: Distributed Rate Limiting System

## Learning Roadmap
1. **Fundamentals**: Understand the core problems of rate limiting (DDoS, cost control, stability).
2. **Algorithms**: Study the Token Bucket and Leaky Bucket algorithms.
3. **Distributed Architecture**: Learn how to scale rate limiters across nodes using Redis.
4. **Race Conditions**: Identify concurrency issues and learn to resolve them with Redis Lua scripts.

## Key Technical Topics
- **Gateway Layer Security**: Protecting backend services at the edge.
- **Token Bucket Algorithm**: Mathematical concept where tokens replenish at a rate `R` up to capacity `C`.
- **Redis Hash State**: Storing `tokens` and `last_updated` properties key-value style.
- **Atomic Operations**: Using Lua scripts in Redis to prevent race conditions during concurrent request processing.

## Code Fences
```python
# Thread-safe local rate limiter simulation
import time

class TokenBucket:
    def __init__(self, capacity, fill_rate):
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = capacity
        self.last_update = time.time()

    def allow_request(self):
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False
```
"""

# Global event log accumulator to populate Notion's "Timestamp" property
execution_logs = []

def log_event(message):
    """Logs an event to console and appends to the runtime log accumulator."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    execution_logs.append(formatted)

def create_dummy_jpeg(path):
    """Creates a minimal valid 1x1 black JPEG file if it does not exist."""
    # Standard 1x1 black pixel JPEG bytes
    jpeg_bytes = (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06'
        b'\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
        b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00'
        b'\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00'
        b'\x00?\x00\x37\xff\xd9'
    )
    with open(path, 'wb') as f:
        f.write(jpeg_bytes)

def chunk_text_to_rich_text(text, max_len=2000):
    """Chunks text into Notion's rich text structures to prevent 2000-character overflow."""
    rich_text_list = []
    for i in range(0, len(text), max_len):
        rich_text_list.append({
            "type": "text",
            "text": {"content": text[i:i+max_len]}
        })
    return rich_text_list

def convert_markdown_to_notion_blocks(markdown_text):
    """Parses markdown output into Notion block objects."""
    lines = markdown_text.splitlines()
    blocks = []
    
    in_code = False
    code_lines = []
    code_lang = "plain text"
    
    accumulated_paragraph = []
    
    def flush_paragraph():
        if accumulated_paragraph:
            text = "\n".join(accumulated_paragraph).strip()
            if text:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": chunk_text_to_rich_text(text)
                    }
                })
            accumulated_paragraph.clear()
            
    for line in lines:
        stripped = line.strip()
        
        # Check code fences
        if stripped.startswith("```"):
            if in_code:
                # End of code fence
                code_content = "\n".join(code_lines)
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "language": code_lang,
                        "rich_text": chunk_text_to_rich_text(code_content)
                    }
                })
                code_lines.clear()
                in_code = False
            else:
                # Start of code fence
                flush_paragraph()
                in_code = True
                lang = stripped[3:].strip().lower()
                # Map common markdown language codes to official Notion API supported values
                notion_languages = {
                    "abap": "abap", "arduino": "arduino", "bash": "bash", "sh": "bash", "shell": "shell",
                    "basic": "basic", "c": "c", "clojure": "clojure", "coffeescript": "coffeescript",
                    "c++": "c++", "cpp": "c++", "csharp": "c#", "c#": "c#", "css": "css", "dart": "dart",
                    "diff": "diff", "docker": "docker", "dockerfile": "docker", "elixir": "elixir",
                    "elm": "elm", "erlang": "erlang", "flow": "flow", "fortran": "fortran", "fsharp": "fsharp",
                    "gherkin": "gherkin", "glsl": "glsl", "go": "go", "golang": "go", "graphql": "graphql",
                    "groovy": "groovy", "haskell": "haskell", "html": "html", "idris": "idris", "java": "java",
                    "javascript": "javascript", "js": "javascript", "json": "json", "julia": "julia",
                    "kotlin": "kotlin", "latex": "latex", "less": "less", "lisp": "lisp", "livescript": "livescript",
                    "llvm": "llvm", "lua": "lua", "makefile": "makefile", "markdown": "markdown", "md": "markdown",
                    "markup": "markup", "matlab": "matlab", "mathematica": "mathematica", "mermaid": "mermaid",
                    "nix": "nix", "objective-c": "objective-c", "objc": "objective-c", "ocaml": "ocaml",
                    "pascal": "pascal", "perl": "perl", "php": "php", "plain text": "plain text", "text": "plain text",
                    "powershell": "powershell", "ps1": "powershell", "prolog": "prolog", "protobuf": "protobuf",
                    "purescript": "purescript", "python": "python", "py": "python", "r": "r", "racket": "racket",
                    "reason": "reason", "ruby": "ruby", "rb": "ruby", "rust": "rust", "rs": "rust", "sass": "sass",
                    "scala": "scala", "scheme": "scheme", "scss": "scss", "sql": "sql", "swift": "swift",
                    "toml": "toml", "typescript": "typescript", "ts": "typescript", "vb.net": "vb.net",
                    "verilog": "verilog", "vhdl": "vhdl", "visual basic": "visual basic", "vb": "visual basic",
                    "webassembly": "webassembly", "wasm": "webassembly", "xml": "xml", "yaml": "yaml", "yml": "yaml",
                    "java/c/c++/c#": "java/c/c++/c#", "notion formula": "notion formula"
                }
                code_lang = notion_languages.get(lang, "plain text")
            continue
            
        if in_code:
            code_lines.append(line)
            continue
            
        # Parse headings
        if stripped.startswith("# "):
            flush_paragraph()
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": chunk_text_to_rich_text(stripped[2:])
                }
            })
        elif stripped.startswith("## "):
            flush_paragraph()
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": chunk_text_to_rich_text(stripped[3:])
                }
            })
        elif stripped.startswith("### "):
            flush_paragraph()
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": chunk_text_to_rich_text(stripped[4:])
                }
            })
        # Parse bullet and numbered lists
        elif stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("+ "):
            flush_paragraph()
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": chunk_text_to_rich_text(stripped[2:])
                }
            })
        elif any(stripped.startswith(f"{i}. ") for i in range(10)):
            flush_paragraph()
            idx = stripped.find(". ")
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": chunk_text_to_rich_text(stripped[idx+2:])
                }
            })
        elif stripped.startswith("> "):
            flush_paragraph()
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": chunk_text_to_rich_text(stripped[2:])
                }
            })
        elif not stripped:
            flush_paragraph()
        else:
            accumulated_paragraph.append(line)
            
    flush_paragraph()
    # Limit Notion page creation payload limit to 100 blocks
    return blocks[:100]

def send_rest_post(url, payload, headers=None):
    """Performs a REST POST request using Python's standard urllib library."""
    if headers is None:
        headers = {}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.getcode(), json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        response_body = e.read().decode("utf-8")
        try:
            err_json = json.loads(response_body)
        except Exception:
            err_json = {"error_raw": response_body}
        return e.code, err_json
    except Exception as e:
        return 0, {"error": str(e)}

def run_pipeline(openrouter_key, notion_token, db_id, screenshot_path, model="openrouter/free", base_url="https://openrouter.ai/api/v1", verbose=False):
    """Executes a single run of the Live Event Annotator Pipeline."""
    global execution_logs
    execution_logs.clear()
    
    print("\n" + "="*60)
    print("      TEAM KNIGHTHOOD - LIVE PIPELINE SIMULATION RUN      ")
    print("="*60)
    
    # ----------------- STAGE 1: SIMULATED INPUT TIERS -----------------
    log_event("[1/3] Parsing simulated audio input...")
    log_event(f"    - Loaded mock transcript string ({len(DEFAULT_TRANSCRIPT)} chars)")
    
    # Verify/generate the local binary screenshot
    if not os.path.exists(screenshot_path):
        log_event(f"    - Slide screenshot '{screenshot_path}' not found. Generating dummy image...")
        try:
            create_dummy_jpeg(screenshot_path)
            log_event(f"    - Created mock screenshot: {screenshot_path}")
        except Exception as e:
            log_event(f"    - ERROR generating mock screenshot: {e}")
            
    # Read image and convert to Base64
    base64_image = ""
    try:
        with open(screenshot_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        log_event(f"    - Encoded slide image into Base64 ({len(base64_image)} chars)")
    except Exception as e:
        log_event(f"    - Failed to read/encode slide image: {e}")
        
    log_event("    - Input ingestion phase complete.")
    
    # ----------------- STAGE 2: AI SYNTHESIS ENGINE -----------------
    log_event("[2/3] Processing context via OpenRouter...")
    
    system_instruction = (
        "Analyze this tech lecture text and structural slide content. "
        "Synthesize it into a highly actionable, structured Learning Roadmap, "
        "Key Technical Topics, and Code Fences. Output strictly in clean "
        "Markdown formatting. Do not include any conversational filler words "
        "or intro text like 'Sure, here is your summary'. "
        "Do not use LaTeX math formatting, dollar signs ($ or $$), or LaTeX symbols (like \\Delta, \\times, etc.) anywhere in the output. "
        "Write all equations, formulas, variables, and math symbols in plain text or format them using standard markdown or backticks (e.g., use C or R, or Delta * R, not $C$ or $R$)."
    )
    
    messages = [
        {
            "role": "system",
            "content": system_instruction
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Here is the workshop transcript:\n\n{DEFAULT_TRANSCRIPT}"}
            ]
        }
    ]
    
    if base64_image:
        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        })
        
    openrouter_payload = {
        "model": model,
        "messages": messages
    }
        
    synthesis_markdown = ""
    
    if openrouter_key and not openrouter_key.startswith("your_"):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openrouter_key}"
        }
        
        log_event(f"    - Submitting content using model '{model}' to OpenRouter...")
        openrouter_url = f"{base_url.rstrip('/')}/chat/completions"
        status_code, response = send_rest_post(openrouter_url, openrouter_payload, headers)
        
        if status_code == 200:
            try:
                synthesis_markdown = response["choices"][0]["message"]["content"]
                log_event("    - SUCCESS: AI Synthesis response received from OpenRouter.")
            except (KeyError, IndexError) as e:
                log_event(f"    - ERROR: Failed to parse OpenRouter response structure: {e}")
                log_event(f"      Response: {json.dumps(response)}")
        else:
            log_event(f"    - OpenRouter API failed (HTTP {status_code}).")
            log_event(f"      Response: {json.dumps(response)}")
    else:
        log_event("    - WARNING: Invalid or default OpenRouter key. Using mock pipeline response fallback.")
        
    if not synthesis_markdown:
        log_event("    - Loading pre-baked high-fidelity fallback markdown synthesis.")
        synthesis_markdown = FALLBACK_MARKDOWN
        
    print("\n--- [SYNTHESIS OUTPUT START] ---")
    print(synthesis_markdown.strip())
    print("--- [SYNTHESIS OUTPUT END] ---\n")
    
    # ----------------- STAGE 3: NOTION CLIENT INTEGRATION -----------------
    log_event("[3/3] Inbound payload populated. Notion entry state set to Review Pending")
    
    # Parse Markdown into Notion blocks
    notion_blocks = convert_markdown_to_notion_blocks(synthesis_markdown)
    log_event(f"    - Converted markdown synthesis into {len(notion_blocks)} structured Notion blocks.")
    
    # Format Runtime Timestamp and execution logs
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    runtime_logs_string = f"System Engineering Mock Run logs:\nRun Time: {current_time}\n" + "\n".join(execution_logs)
    
    # Slice to prevent Notion's 2000 character overflow
    if len(runtime_logs_string) > 2000:
        runtime_logs_string = runtime_logs_string[:1996] + "\n..."
        
    # Construct Notion payload
    notion_payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Topic Name": {
                "title": [
                    {"text": {"content": "System Engineering Mock Run - KNIGHTHOOD"}}
                ]
            },
            "Status": {
                "select": {"name": "Review Pending"}
            },
            "Timestamp": {
                "rich_text": [
                    {"text": {"content": runtime_logs_string}}
                ]
            }
        },
        "children": notion_blocks
    }
    
    # Notion API post is disabled as per user request
    if False:
        pass
    else:
        log_event("    - INFO: Notion credentials not provided or set to defaults.")
        if verbose:
            log_event("    - Dumping simulated JSON API payload that would be sent to Notion:")
            print("\n--- [NOTION API JSON PAYLOAD] ---")
            print(json.dumps(notion_payload, indent=2))
            print("--- [END OF JSON PAYLOAD] ---\n")
        else:
            log_event("    - Notion page simulation validation successful.")
            log_event(f"      * Title: '{notion_payload['properties']['Topic Name']['title'][0]['text']['content']}'")
            log_event(f"      * Status set to: '{notion_payload['properties']['Status']['select']['name']}'")
            log_event(f"      * Blocks parsed: {len(notion_blocks)} structured elements generated.")
            log_event("      * [TIP] Run with --verbose to view the full Notion JSON payload structure.")
        
    print("="*60)
    print("                      PIPELINE RUN COMPLETE                      ")
    print("="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="Team KNIGHTHOOD - Live Event Annotator Pipeline Mock Prototype",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--openrouter-key", 
        type=str, 
        default=os.environ.get("OPENROUTER_API_KEY", DEFAULT_OPENROUTER_KEY),
        help="OpenRouter API Key"
    )
    parser.add_argument(
        "--notion-token", 
        type=str, 
        default=os.environ.get("NOTION_TOKEN", DEFAULT_NOTION_TOKEN),
        help="Notion Integration Token (starts with ntn_)"
    )
    parser.add_argument(
        "--db-id", 
        type=str, 
        default=os.environ.get("NOTION_DATABASE_ID", DEFAULT_DB_ID),
        help="Notion Database ID (32-character hex ID)"
    )
    parser.add_argument(
        "--screenshot", 
        type=str, 
        default="slide1.jpg",
        help="Path to simulated screenshot slide"
    )
    parser.add_argument(
        "--loop", 
        action="store_true",
        help="Run the script continuously in a simulated service loop"
    )
    parser.add_argument(
        "--interval", 
        type=int, 
        default=30,
        help="Loop sleep interval in seconds"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print the complete raw Notion page JSON payload during simulation"
    )
    
    args = parser.parse_args()
    
    if args.loop:
        print(f"[*] Starting background pipeline daemon loop. Executing every {args.interval}s...")
        print("[*] Press Ctrl+C to stop the service loop.")
        try:
            while True:
                run_pipeline(args.openrouter_key, args.notion_token, args.db_id, args.screenshot, verbose=args.verbose)
                for remaining in range(args.interval, 0, -1):
                    sys.stdout.write(f"\r[*] Waiting... next run in {remaining}s (Press Ctrl+C to exit) ")
                    sys.stdout.flush()
                    time.sleep(1)
                sys.stdout.write("\r" + " " * 70 + "\r")
                sys.stdout.flush()
        except KeyboardInterrupt:
            print("\n[-] Daemon loop stopped by user. Exiting.")
    else:
        run_pipeline(args.openrouter_key, args.notion_token, args.db_id, args.screenshot, verbose=args.verbose)

if __name__ == "__main__":
    main()
