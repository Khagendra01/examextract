"""
Exam paper extractor — supports OpenRouter (mimo-v2.5) and Google AI Studio (Gemini).

Upload images → AI extracts structured JSON → ExamDocument → DOCX with proper formatting.
No database, no state — just clean in/out.

For local development: python app_exam.py
"""
import os
import re
import json
import base64
import mimetypes
import tempfile
from io import BytesIO

from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
import requests

from exam_schema import ExamDocument
from template import build_exam_docx

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_API_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEY", "").split(",") if k.strip()]

# Model configs
MODELS = {
    "mimo": {
        "provider": "openrouter",
        "name": "xiaomi/mimo-v2.5",
        "label": "Mimo v2.5 (OpenRouter)",
    },
    "gemini": {
        "provider": "google",
        "name": "gemini-3-flash-preview",
        "label": "Gemini 3 Flash Preview (Google AI Studio)",
    },
}

EXTRACTION_PROMPT = """You are an expert at extracting structured data from exam documents. Extract ONLY what you can actually SEE in the image. DO NOT add, invent, or infer information that is not visible.

FUNDAMENTAL RULE: Extract ONLY what is VISIBLE in the image. Never add information that doesn't exist in the document.

EXTRACTION REQUIREMENTS:

1. **Exam Title**: Extract the main title ONLY if it is visible in the image. If no title is visible, use a simple descriptive title based on subject (e.g., "Math Exam", "Science Exam") or null.

2. **Metadata**: Extract header information ONLY if visible:
   - Subject (Sub): Extract exactly as written (e.g., "Science", "Mathematics", "Math", "math.") - preserve the exact text
   - Full Marks (FM or F.M): Extract if visible (e.g., "50", "100")
   - Class: Extract if visible (e.g., "6", "10", "class-6")
   - Time: Extract ONLY if visible in the image - otherwise null
   - Pass Marks (PM): Extract ONLY if visible in the image - otherwise null

3. **Instructions**: Extract instruction lines ONLY if they are visible between the metadata and questions (e.g., "Attempt the questions.", "Answer all questions."). If not visible, set to null.

4. **Sections**: CRITICAL RULES:
   - **SECTION TITLE RULE**: Extract section title ONLY if you can actually SEE it written in the image. If there is NO visible section title (like "Part 1", "Part 2", "Section A", etc.), you MUST set "title" to null.
   - **ABSOLUTELY FORBIDDEN**: DO NOT add "Part 1", "Part I", or any default section title if it's not actually written in the image!
   - Section Number: Use "1" for the first (and possibly only) section
   - Section Title: null if not visible, or the exact text if visible
   - Scoring: Extract ONLY if visible (e.g., "(10*1=10)", "7x2=14") - otherwise null
   - Questions: Extract ALL questions in sequential order
     - Question Label: The main question identifier (e.g., "1", "2", "3", "4")
     - Question Text: The main question text
     - Sub-questions: ONLY use sub_questions if the sub-parts (a, b, i, ii) are CLEARLY part of the main question
     - Options: If it's a multiple choice question, extract all options with label and text

OUTPUT FORMAT:

Output ONLY valid JSON in this exact format (no markdown, no code blocks, just pure JSON):

{
  "title": "Exam Title Here",
  "metadata": {
    "subject": "Subject Name",
    "full_marks": "Full Marks",
    "class_level": "Class/Grade",
    "time": "Time Duration or null",
    "pass_marks": "Pass Marks or null"
  },
  "instructions": "Instruction text or null",
  "nueva": null,
  "sections": [
    {
      "number": "1",
      "title": null,
      "scoring": null,
      "nueva": null,
      "questions": [
        {
          "label": "1",
          "text": "Main Question Text",
          "sub_questions": [
            {
              "label": "a",
              "text": "Sub-question text",
              "nueva": null
            }
          ],
          "options": [
            {
              "label": "i",
              "text": "Option Text"
            }
          ],
          "nueva": null
        }
      ]
    }
  ]
}

IMPORTANT:
- Output ONLY valid JSON, no markdown, no code blocks
- Use null for missing optional fields
- All text values must be strings
- Preserve the exact text as it appears in the document
- Include marks notation like [2] in question text
- Use "nueva" field for any content that doesn't fit standard structure

Now extract the exam data from this image:"""


def guess_mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "image/png"


def extract_json_from_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text.strip()


# ============================================================
# OpenRouter (mimo-v2.5)
# ============================================================
def call_openrouter(prompt: str, image_paths: list, model_name: str) -> dict:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    }

    content = [{"type": "text", "text": prompt}]
    for p in image_paths:
        mime = guess_mime(p)
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        })

    resp = requests.post(
        url,
        json={
            "model": model_name,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.2,
        },
        headers=headers,
        timeout=180,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter API failed ({resp.status_code}): {resp.text[:500]}")

    data = resp.json()
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not text:
        raise RuntimeError("Empty OpenRouter response")
    return text


# ============================================================
# Google AI Studio (Gemini) — with key rotation
# ============================================================
def call_gemini(prompt: str, image_parts: list) -> dict:
    import random

    if not GEMINI_API_KEYS:
        raise RuntimeError("No GEMINI_API_KEYs configured")

    # Shuffle keys to spread load across all 4
    keys = list(GEMINI_API_KEYS)
    random.shuffle(keys)

    last_error = None
    for api_key in keys:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELS['gemini']['name']}:generateContent?key={api_key}"

        parts = [{"text": prompt}]
        for mime, b64 in image_parts:
            parts.append({
                "inline_data": {
                    "mime_type": mime,
                    "data": b64,
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.2,
            },
        }

        try:
            resp = requests.post(url, json=payload, timeout=180)

            # Rate limited or server error — try next key
            if resp.status_code in (429, 500, 503):
                last_error = f"Key ...{api_key[-6:]} got {resp.status_code}"
                continue

            if resp.status_code != 200:
                last_error = f"Gemini API failed ({resp.status_code}): {resp.text[:300]}"
                continue

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                last_error = "No candidates in Gemini response"
                continue

            parts_out = candidates[0].get("content", {}).get("parts", [])
            text = parts_out[0].get("text", "") if parts_out else ""
            if not text:
                last_error = "Empty Gemini response"
                continue

            return text  # Success — return immediately

        except requests.Timeout:
            last_error = f"Key ...{api_key[-6:]} timed out"
            continue

    raise RuntimeError(f"All Gemini keys failed. Last error: {last_error}")


# ============================================================
# Unified LLM call
# ============================================================
def call_llm(prompt: str, image_paths: list, model_key: str = "mimo") -> dict:
    config = MODELS.get(model_key)
    if not config:
        raise ValueError(f"Unknown model: {model_key}")

    if config["provider"] == "google":
        if not GEMINI_API_KEYS:
            raise RuntimeError("No GEMINI_API_KEYs configured")
        # Read images into (mime, base64) pairs
        image_parts = []
        for p in image_paths:
            mime = guess_mime(p)
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            image_parts.append((mime, b64))
        raw_text = call_gemini(prompt, image_parts)
    else:
        if not OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY not set")
        raw_text = call_openrouter(prompt, image_paths, config["name"])

    json_str = extract_json_from_text(raw_text)
    parsed = json.loads(json_str)

    if not isinstance(parsed, dict):
        raise ValueError("Response is not a JSON object")
    return parsed


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "models": {
            "mimo": {"available": bool(OPENROUTER_API_KEY)},
            "gemini": {"available": len(GEMINI_API_KEYS) > 0, "keys_count": len(GEMINI_API_KEYS)},
        },
    })


@app.route("/api/extract", methods=["POST"])
def extract():
    if "images" not in request.files:
        return jsonify({"error": "No images uploaded"}), 400

    # Orientation from form field (default: landscape)
    orientation = request.form.get("orientation", "landscape")
    if orientation not in ("landscape", "portrait"):
        orientation = "landscape"

    # Model selection (default: mimo)
    model_key = request.form.get("model", "mimo")
    if model_key not in MODELS:
        model_key = "mimo"

    # Check API key availability
    config = MODELS[model_key]
    if config["provider"] == "google" and not GEMINI_API_KEYS:
        return jsonify({"error": "No GEMINI_API_KEYs configured — cannot use Gemini"}), 400
    if config["provider"] == "openrouter" and not OPENROUTER_API_KEY:
        return jsonify({"error": "OPENROUTER_API_KEY not set — cannot use Mimo"}), 400

    temp_files = []
    try:
        for f in request.files.getlist("images"):
            path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
            f.save(path)
            temp_files.append(path)

        if not temp_files:
            return jsonify({"error": "No valid images"}), 400

        # 1. Call AI to extract structured JSON
        exam_data = call_llm(EXTRACTION_PROMPT, temp_files, model_key)

        # 2. Parse into ExamDocument
        exam = ExamDocument.from_dict(exam_data)

        # 3. Build DOCX — orientation controls format
        out_buf = BytesIO()
        build_exam_docx(out_buf, exam_data=exam, orientation=orientation)
        out_buf.seek(0)
        docx_bytes = out_buf.read()

        return jsonify({
            "status": "ok",
            "filename": "exam_extract.docx",
            "docx_base64": base64.b64encode(docx_bytes).decode("utf-8"),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        for p in temp_files:
            try:
                os.remove(p)
            except OSError:
                pass


if __name__ == "__main__":
    app.run(debug=True, port=5000)
