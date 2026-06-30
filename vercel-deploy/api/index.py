"""
Exam paper extractor — structured extraction using ExamDocument schema.

Upload images → AI extracts structured JSON → ExamDocument → DOCX with proper formatting.

Vercel: auto-detected as WSGI app via 'app = Flask(__name__)'
Local: python index.py
"""
import os
import re
import json
import base64
import mimetypes
import tempfile
from io import BytesIO
from typing import Optional

from flask import Flask, request, jsonify, send_file, render_template
import requests

from exam_schema import ExamDocument
from template import build_exam_docx

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = "xiaomi/mimo-v2.5"

# ============================================================
# Extraction prompt — tells AI to return structured ExamDocument JSON
# ============================================================
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
   - Section Title: null if not visible, or the exact text if visible (e.g., "Multiple Choice Questions", "Part 1" - but ONLY if actually written)
   - Scoring: Extract ONLY if visible (e.g., "(10*1=10)", "7x2=14") - otherwise null
   - Questions: Extract ALL questions in sequential order (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14...)
     - Question Label: The main question identifier (e.g., "1", "2", "3", "4"). Follow the actual question numbering in the document
     - Question Text: The main question text. If a question has sub-parts that are DIRECTLY related to it, extract them as sub_questions
     - Sub-questions: ONLY use sub_questions if the sub-parts (a, b, i, ii) are CLEARLY part of the main question
       - Example: Question "1" says "write the following in set notation" and has "a) 2 belongs..." and "b) 5 does not belong..." - these ARE sub-questions of question 1
       - Example: Question "4" says "write the set of prime numbers less than 10" - if there are separate questions "a)" and "b)" about factorization that come AFTER, they are NOT sub-questions of question 4, they are separate questions
     - Options: If it's a multiple choice question, extract all options:
       - Option Label: The option identifier (e.g., "i", "ii", "iii", "iv", "A", "B", "C", "D")
       - Option Text: The option text

CRITICAL STRUCTURE RULES:

1. **Two-Column Layout**: CRITICAL - If questions are in two columns, they are STILL part of the same section. Questions flow sequentially: left column questions first (1, 2, 3...), then right column questions continue the sequence.
   - DO NOT create separate sections for columns!
   - DO NOT use section titles like "Page 1 Right Column", "Left Column", "Right Column", etc.
   - If you see questions in two columns, they ALL belong to ONE section. Use the actual section title from the document, or null if no title exists

2. **Question Numbering**: Follow the ACTUAL question numbers in the document (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14...). Do NOT skip numbers. If question 9 is missing, still include it or note it.

3. **Sub-Questions vs Separate Questions**:
   - Sub-questions belong to a question when they are DIRECTLY answering or completing the main question
   - Example CORRECT: Question "1" says "write the following in set notation [2]" and has "a) 2 belongs..." and "b) 5 does not belong..." - these ARE sub-questions
   - Example WRONG: Question "4" says "write the set of prime numbers less than 10 [1]" - if there are questions "a)" and "b)" about factorization that appear after, they are NOT sub-questions of question 4, they are separate questions with their own numbers

4. **Section Structure**:
   - **MOST IMPORTANT**: Section title MUST be null unless you can actually SEE a section title written in the image!
   - If there's only one continuous exam with no visible section title, use: {"number": "1", "title": null}
   - Only create multiple sections if there are explicit section headers ACTUALLY WRITTEN in the image (like "Part 1", "Part 2", "Section A", "Multiple Choice Questions")
   - NEVER create sections based on page layout, columns, or spatial positioning
   - NEVER use titles containing "Column", "Page", "Left", "Right" unless those words are actually written in the document
   - NEVER infer section titles from question numbering or layout - ONLY use what is explicitly written!

REFERENCE EXAMPLE:

EXAMPLE - Correct extraction when NO section title is visible:
- Header: "class-6" and "sub- math." at top left, "F.M=50" at top right
- Instructions: "Attempt the questions." centered below header
- **CRITICAL**: NO section title like "Part 1" is visible in the image - therefore section title MUST be null
- Two-column layout: Questions 1-6 in left column, Questions 7-14 in right column, but ALL in ONE section
- Questions numbered sequentially: 1, 2, 3, 4, 5, 6, 7, 8, (9 missing?), 10, 11, 12, 13, 14
- Correct section format: {"number": "1", "title": null, "scoring": null}
- Example CORRECT extraction for Question 1:
  {
    "label": "1",
    "text": "write the following in set notation. [2]",
    "sub_questions": [
      {"label": "a", "text": "2 belongs to the set of natural number N"},
      {"label": "b", "text": "5 does not belong to the set N"}
    ]
  }
- Example CORRECT extraction for Question 4:
  {
    "label": "4",
    "text": "write the set of prime numbers less than 10 [1]",
    "sub_questions": null
  }
- If there are separate questions labeled "a)" and "b)" about factorization AFTER question 4, they should be separate questions, NOT sub-questions of question 4

OUTPUT FORMAT:

Output ONLY valid JSON in this exact format (no markdown, no code blocks, just pure JSON):

{
  "title": "Exam Title Here (or descriptive title)",
  "metadata": {
    "subject": "Subject Name",
    "full_marks": "Full Marks",
    "class_level": "Class/Grade",
    "time": "Time Duration (optional, can be null)",
    "pass_marks": "Pass Marks (optional, can be null)"
  },
  "instructions": "Instruction text like 'Attempt the questions.' (optional, can be null)",
  "nueva": null,
  "sections": [
    {
      "number": "1",
      "title": null,
      "scoring": null,
      "nueva": null,
      "questions": [
        {
          "label": "Question Label (main number like 1, 2, 3)",
          "text": "Main Question Text (include marks notation like [2] if present)",
          "sub_questions": [
            {
              "label": "Sub-question label (a, b, i, ii, etc.)",
              "text": "Sub-question text (include marks if present)",
              "nueva": null
            }
          ],
          "options": [
            {
              "label": "Option Label",
              "text": "Option Text"
            }
          ],
          "nueva": null
        }
      ]
    }
  ]
}

HANDLING UNKNOWN/NOVEL CONTENT TYPES:
- If you encounter content that doesn't fit the standard structure (e.g., diagrams, tables, special formatting, new question types), use the "nueva" field
- "nueva" is a flexible field that can store any JSON object for unknown content types
- Example: If you see a diagram or special content type not covered by questions/options, store it in "nueva":
  {
    "label": "a",
    "text": "Standard question text",
    "nueva": {
      "type": "diagram",
      "description": "Diagram showing...",
      "raw_content": "Any additional data about this novel content"
    }
  }
- Use "nueva" at question, section, or document level as needed
- This prevents forcing unknown content into incorrect structures and allows for future schema extensions

IMPORTANT NOTES:
- Output ONLY valid JSON, no markdown formatting, no code blocks
- If a field is not found, use null (for optional fields) or omit it
- For non-multiple-choice questions, set "options" to null
- All text values should be strings (even numbers like "50" for marks)
- Preserve the exact text as it appears in the document
- Section numbers and question labels can be any format (numbers, letters, roman numerals, etc.)
- If scoring format is not explicitly mentioned, you can omit it or infer it from context
- Include instruction lines that appear between header and questions (like "Attempt the questions.")
- CRITICAL: Two-column layout is JUST layout - questions flow sequentially from left to right column within the SAME section
- DO NOT create separate sections based on columns - only create sections for explicit parts or different question types
- Question marks in brackets like [2] should be included in the question text
- Follow the ACTUAL question numbering sequence (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14...)
- IMPORTANT: Only use "sub_questions" when sub-parts (a, b, i, ii) are DIRECTLY part of the main question
- If a question like "1" says "write the following" and has "a)" and "b)" that complete it, those ARE sub-questions
- If question "4" is about prime numbers and there are separate "a)" and "b)" questions about factorization that come after, they are NOT sub-questions - they are separate questions
- When in doubt, if a question with a letter/number label appears AFTER another question and seems independent, it's a separate question, not a sub-question
- If you encounter content that doesn't fit standard question/option structure, use "nueva" field instead of forcing it into incorrect format

Now extract the exam data from this image:"""


def guess_mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "image/png"


def extract_json_from_text(text: str) -> str:
    """Extract JSON from text response, handling markdown code blocks."""
    text = text.strip()
    # Remove markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    # Find JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text.strip()


def call_llm(prompt: str, image_paths: list) -> dict:
    """Call OpenRouter API with images, return parsed JSON."""
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


# ============================================================
# Flask app (works for both Vercel serverless AND local dev)
# ============================================================
app = Flask(__name__, template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


@app.route("/")
def index():
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "index.html")
    if os.path.exists(html_path):
        with open(html_path) as f:
            return f.read()
    return "ExamExtract - template not found", 404


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
            path = os.path.join(tempfile.gettempdir(), f.filename)
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
        docx_bytes = out_buf.read()

        # Return as JSON with base64 — send_file breaks in Vercel WSGI bridge
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
