"""
Exam paper extractor — structured extraction using ExamDocument schema.

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

from flask import Flask, request, render_template, send_file, jsonify
from dotenv import load_dotenv
import requests

from exam_schema import ExamDocument
from template import build_exam_docx

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "xiaomi/mimo-v2.5"

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
   - **ABSOLUTELY FORBIDDEN**: DO NOT infer or invent section titles based on layout, column structure, or question numbering!
   - If the exam has two columns, they are just layout - questions flow from left column to right column within the same section
   - Section Number: Use "1" for the first (and possibly only) section
   - Section Title: null if not visible, or the exact text if visible
   - Scoring: Extract ONLY if visible (e.g., "(10*1=10)", "7x2=14") - otherwise null
   - Questions: Extract ALL questions in sequential order
     - Question Label: The main question identifier (e.g., "1", "2", "3", "4")
     - Question Text: The main question text
     - Sub-questions: ONLY use sub_questions if the sub-parts (a, b, i, ii) are CLEARLY part of the main question
     - Options: If it's a multiple choice question, extract all options with label and text

CRITICAL STRUCTURE RULES:

1. **Two-Column Layout**: Questions in two columns are STILL part of the same section. Questions flow sequentially from left to right.
   - DO NOT create separate sections for columns!

2. **Question Numbering**: Follow the ACTUAL question numbers. Do NOT skip numbers.

3. **Sub-Questions vs Separate Questions**:
   - Sub-questions belong to a question when they are DIRECTLY answering or completing the main question
   - If a question with a letter/number label appears AFTER another question and seems independent, it's a separate question, not a sub-question

4. **Section Structure**:
   - Section title MUST be null unless you can actually SEE a section title written in the image!
   - Only create multiple sections if there are explicit section headers ACTUALLY WRITTEN in the image
   - NEVER create sections based on page layout, columns, or spatial positioning

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


def call_llm(prompt: str, image_paths: list) -> dict:
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
            "model": MODEL,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.2,
        },
        headers=headers,
        timeout=180,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"API failed ({resp.status_code}): {resp.text[:500]}")

    data = resp.json()
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not text:
        raise RuntimeError("Empty API response")

    json_str = extract_json_from_text(text)
    parsed = json.loads(json_str)

    if not isinstance(parsed, dict):
        raise ValueError("Response is not a JSON object")
    return parsed


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "model": MODEL, "extraction": "structured"})


@app.route("/api/extract", methods=["POST"])
def extract():
    if not OPENROUTER_API_KEY:
        return jsonify({"error": "OPENROUTER_API_KEY not set"}), 500

    if "images" not in request.files:
        return jsonify({"error": "No images uploaded"}), 400

    temp_files = []
    try:
        for f in request.files.getlist("images"):
            path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
            f.save(path)
            temp_files.append(path)

        if not temp_files:
            return jsonify({"error": "No valid images"}), 400

        # 1. Call AI to extract structured JSON
        exam_data = call_llm(EXTRACTION_PROMPT, temp_files)

        # 2. Parse into ExamDocument
        exam = ExamDocument.from_dict(exam_data)

        # 3. Build DOCX using template.py's proper formatting
        out_buf = BytesIO()
        build_exam_docx(out_buf, exam_data=exam)
        out_buf.seek(0)

        return send_file(
            out_buf,
            as_attachment=True,
            download_name="exam_extract.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

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
