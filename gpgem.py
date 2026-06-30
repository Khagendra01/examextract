import argparse
import base64
import json
import mimetypes
import os
import re
from typing import List, Dict, Any

import requests


ALLOWED = {"T", "M", "R", "S", "Q", "O", "P"}

MODEL_DEFAULT = "xiaomi/mimo-v2.5"


def guess_mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "image/png"


def b64_file(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def load_template(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def build_prompt(template_text: str) -> str:
    # Keep it short + strict. The schema enforces structure.
    return f"""
You are converting an exam paper image into a compact tag+text format.

RETURN A JSON ARRAY. Each element must be an object:
  {{ "tag": "T|M|R|S|Q|O|P", "text": "<line text>" }}

STRICT RULES:
- tag must be one of: T, M, R, S, Q, O, P
- Use O for any inner/sub part like: a. b. i. ii. iii. (a) (i) etc
- Use Q for main questions like: 1. 2. 3. ... or a. b. (when they are main questions)
- Use S for section headers (e.g. "1. Multiple Choice Questions...")
- Use M for meta lines (Class/Sub/FM/PM/Time etc). Prefer tabs as \\t inside the text.
- Use R for separators or anything unclear.
- Use the literal sequence "\\t" for alignment (NOT real tab characters).
- No blank lines. No markdown. No extra commentary.

Follow this style (template example):
{template_text}
""".strip()


SUBPART_RE = re.compile(
    r"""^(
        \(?[a-z]\) |          # a) or (a)
        \(?[ivxlcdm]+\)       # i) ii) iv) or (i) (ii)
    )\s+""",
    re.IGNORECASE | re.VERBOSE,
)

ROMAN_INLINE_OPTIONS_RE = re.compile(r"\bi\.\s|ii\.\s|iii\.\s|iv\.\s", re.IGNORECASE)


def force_tag_rules(tag: str, text: str) -> str:
    """
    Post rules:
    - unknown tags -> R
    - if looks like a subpart -> O
    - if contains inline roman option list -> O
    """
    t = (tag or "R").strip().upper()
    if t not in ALLOWED:
        t = "R"

    s = (text or "").strip()

    # Normalize real tabs to literal \t (in case model emits tabs)
    s = s.replace("\t", "\\t")

    low = s.lower()

    # Heuristic fix: OCR sometimes reads "y)" for "9)"
    if low.startswith("y) "):
        s = "9) " + s[3:]

    # If the line begins with subpart markers, make it O
    if t in {"Q", "O"} and SUBPART_RE.match(low):
        return "O"

    # If it contains packed i./ii./iii./iv. style options, make it O
    if t in {"Q", "O"} and ("\\t" in s or ROMAN_INLINE_OPTIONS_RE.search(s)):
        # Only force to O if it really looks like options/subitems
        if " i." in (" " + low) or " ii." in (" " + low) or "\\t" in s:
            return "O"

    return t


def call_llm_json_mode(
    api_key: str,
    model: str,
    prompt: str,
    image_paths: List[str],
    temperature: float = 0.2,
) -> List[Dict[str, Any]]:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    content_parts = [{"type": "text", "text": prompt}]
    for p in image_paths:
        mime = guess_mime(p)
        b64 = b64_file(p)
        content_parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            }
        )

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content_parts}],
        "temperature": temperature,
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=180)
    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter API failed ({resp.status_code}): {resp.text}")

    data = resp.json()

    # Extract text from OpenAI-compatible format
    choices = data.get("choices", [])
    if not choices or "message" not in choices[0]:
        raise RuntimeError(f"OpenRouter API returned no choices. Response: {json.dumps(data, indent=2)}")

    text = choices[0]["message"].get("content", "")
    if not text:
        raise RuntimeError("OpenRouter API returned empty content.")

    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    parsed = json.loads(text)

    if not isinstance(parsed, list):
        raise ValueError("JSON mode did not return a list")

    return parsed

# Keep backward-compatible alias
call_gemini_json_mode = call_llm_json_mode


def normalize_question_labels(text: str) -> str:
    """Convert question labels from ')' to '.' format (e.g., '1)' -> '1.')"""
    # Pattern to match question labels like "1)", "2)", etc. at the start of Q: lines
    # Also handle cases like "Q: 1) text" -> "Q: 1. text"
    pattern = r'^(Q:\s*)(\d+)\)\s*'
    return re.sub(pattern, r'\1\2. ', text, flags=re.MULTILINE)


def normalize_required_fields(lines: List[str]) -> List[str]:
    """
    Ensure required fields are present:
    - T: line must always be present
    - M: lines should have placeholders for Sub:, Class:, Time:, FM:, PM: if missing
    """
    normalized = []
    has_title = False
    meta_lines = []
    other_lines = []
    
    # Separate lines by type
    for line in lines:
        if line.startswith("T:"):
            has_title = True
            normalized.append(line)
        elif line.startswith("M:"):
            meta_lines.append(line)
        else:
            other_lines.append(line)
    
    # Ensure T: is always present
    if not has_title:
        normalized.insert(0, "T: Third Terminal Examination 2082")
    
    # Process metadata lines
    # Extract existing fields from M: lines
    has_sub = False
    has_fm = False
    has_class = False
    has_time = False
    has_pm = False
    sub_value = ""
    fm_value = ""
    class_value = ""
    time_value = ""
    pm_value = ""
    
    for meta_line in meta_lines:
        text = meta_line[2:].strip()  # Remove "M: " prefix
        # Replace literal \t with a marker for easier parsing
        text_normalized = text.replace("\\t", "\t")
        
        # Check for Sub: - improved regex to handle various formats
        # Match "Sub:" followed by non-empty value (not just tab or empty)
        sub_match = re.search(r'Sub:\s*([^\t\n]+?)(?:\t|$|FM:)', text_normalized)
        if sub_match:
            val = sub_match.group(1).strip()
            if val and val not in ['-', '']:
                has_sub = True
                sub_value = val
        
        # Check for FM: - improved regex
        fm_match = re.search(r'FM:\s*([^\t\n]+?)(?:\t|$)', text_normalized)
        if fm_match:
            val = fm_match.group(1).strip()
            if val and val not in ['-', '']:
                has_fm = True
                fm_value = val
        
        # Check for Class:
        class_match = re.search(r'Class:\s*([^\t\n]+?)(?:\t|$|Time:)', text_normalized)
        if class_match:
            val = class_match.group(1).strip()
            if val and val not in ['-', '']:
                has_class = True
                class_value = val
        
        # Check for Time:
        time_match = re.search(r'Time:\s*([^\t\n]+?)(?:\t|$|PM:)', text_normalized)
        if time_match:
            val = time_match.group(1).strip()
            if val and val not in ['-', '']:
                has_time = True
                time_value = val
        
        # Check for PM:
        pm_match = re.search(r'PM:\s*([^\t\n]+?)(?:\t|$)', text_normalized)
        if pm_match:
            val = pm_match.group(1).strip()
            if val and val not in ['-', '']:
                has_pm = True
                pm_value = val
    
    # Build normalized metadata lines with placeholders
    # Line 1: Sub: and FM:
    meta_line1_parts = []
    if has_sub:
        meta_line1_parts.append(f"Sub:{sub_value}")
    else:
        meta_line1_parts.append("Sub:")
    if has_fm:
        meta_line1_parts.append(f"FM: {fm_value}")
    else:
        meta_line1_parts.append("FM:")
    
    if meta_line1_parts:
        normalized.append("M: " + "\\t".join(meta_line1_parts))
    
    # Line 2: Class:, Time:, and PM:
    meta_line2_parts = []
    if has_class:
        meta_line2_parts.append(f"Class: {class_value}")
    else:
        meta_line2_parts.append("Class:")
    if has_time:
        meta_line2_parts.append(f"Time: {time_value}")
    else:
        meta_line2_parts.append("Time:")
    if has_pm:
        meta_line2_parts.append(f"PM: {pm_value}")
    else:
        meta_line2_parts.append("PM:")
    
    if meta_line2_parts:
        normalized.append("M: " + "\\t".join(meta_line2_parts))
    
    # Add other lines and normalize question labels
    normalized_text = "\n".join(normalized + other_lines)
    normalized_text = normalize_question_labels(normalized_text)
    
    return normalized_text.split("\n")


def to_input_lines(items: List[Dict[str, Any]]) -> str:
    out = []
    for it in items:
        tag = str(it.get("tag", "R"))
        text = str(it.get("text", "")).strip()

        tag = force_tag_rules(tag, text)

        # If it's still empty text, keep minimal
        if text:
            # ensure literal \t not real tabs
            text = text.replace("\t", "\\t")
            out.append(f"{tag}: {text}")
        else:
            out.append(f"{tag}:")
    
    # Normalize to ensure required fields are present and fix question labels
    out = normalize_required_fields(out)
    
    return "\n".join(out).strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api_key", default=os.getenv("OPENROUTER_API_KEY"))
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--images", nargs="+", required=True)
    ap.add_argument("--template", default="oldinput.txt")
    ap.add_argument("--out", default="input.txt")
    ap.add_argument("--temperature", type=float, default=0.2)
    args = ap.parse_args()

    if not args.api_key:
        raise SystemExit("Missing API key. Use --api_key or set OPENROUTER_API_KEY env var.")

    template = load_template(args.template)
    prompt = build_prompt(template)

    items = call_gemini_json_mode(
        api_key=args.api_key,
        model=args.model,
        prompt=prompt,
        image_paths=args.images,
        temperature=args.temperature,
    )

    output = to_input_lines(items)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
