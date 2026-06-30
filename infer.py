import base64
import requests
import os
import json
import re
from exam_schema import ExamDocument
from template import build_exam_docx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
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


def extract_json_from_text(text):
    """Extract JSON from text response, handling markdown code blocks."""
    # Try to find JSON in markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    
    # Try to find JSON object directly
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    return text


def fix_column_based_sections(exam_data):
    """
    Post-process extracted exam data to fix sections incorrectly split by columns.
    Merges sections with column-based titles into a single section.
    Preserves all "nueva" fields for unknown content types.
    """
    if "sections" not in exam_data:
        return exam_data
    
    # Check if any section has a column-based title
    column_keywords = ["column", "page", "left", "right"]
    has_column_sections = any(
        any(keyword.lower() in section.get("title", "").lower() 
            for keyword in column_keywords)
        for section in exam_data["sections"]
    )
    
    if not has_column_sections:
        return exam_data  # No fix needed
    
    print("\n⚠ Detected column-based section titles. Merging into single section...")
    
    # Collect all questions from all sections
    all_questions = []
    for section in exam_data["sections"]:
        all_questions.extend(section.get("questions", []))
    
    # Create a single merged section
    merged_section = {
        "number": "1",
        "title": None,  # Don't add default title - only use what's actually in the image
        "scoring": None,
        "questions": all_questions,
        "nueva": None  # Preserve nueva if any section had it
    }
    
    # If there was a non-column section, try to preserve its title (only if it exists)
    for section in exam_data["sections"]:
        title = section.get("title", "").lower() if section.get("title") else ""
        if title and not any(keyword in title for keyword in column_keywords):
            merged_section["title"] = section.get("title")  # Use actual title from image
            merged_section["scoring"] = section.get("scoring")
            if section.get("nueva"):
                merged_section["nueva"] = section.get("nueva")
            break
    
    # Replace all sections with the merged one
    exam_data["sections"] = [merged_section]
    
    print(f"✓ Merged {len(exam_data['sections'])} sections into 1 section with {len(all_questions)} questions")
    
    return exam_data


def main():
    # Load image
    image_path = "image.jpeg"
    if not os.path.exists(image_path):
        print(f"Error: {image_path} not found!")
        return
    
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    # Prepare API request (OpenRouter / OpenAI-compatible format)
    content_parts = [
        {"type": "text", "text": EXTRACTION_PROMPT},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        }
    ]

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": content_parts}],
    }
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    print("Sending request to OpenRouter API (mimo-v2.5)...")
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: API request failed with status {response.status_code}")
        print(response.text)
        return
    
    # Extract response text (OpenAI-compatible format)
    response_data = response.json()
    extracted_text = response_data["choices"][0]["message"]["content"]
    
    print("\n" + "="*60)
    print("Raw AI Response:")
    print("="*60)
    print(extracted_text)
    
    # Extract JSON from response
    json_str = extract_json_from_text(extracted_text)
    
    print("\n" + "="*60)
    print("Extracted JSON:")
    print("="*60)
    print(json_str)
    
    # Parse and validate JSON
    try:
        exam_data = json.loads(json_str)
        print("\n✓ JSON parsed successfully!")
        
        # Fix column-based section splits (post-processing)
        exam_data = fix_column_based_sections(exam_data)
    except json.JSONDecodeError as e:
        print(f"\n✗ Error parsing JSON: {e}")
        print("\nSaving raw response to debug_response.txt for inspection...")
        with open("debug_response.txt", "w", encoding="utf-8") as f:
            f.write(extracted_text)
        return
    
    # Create ExamDocument from extracted data
    try:
        exam = ExamDocument.from_dict(exam_data)
        print(f"\n✓ ExamDocument created successfully!")
        print(f"  Title: {exam.title}")
        print(f"  Subject: {exam.metadata.subject}")
        print(f"  Sections: {len(exam.sections)}")
        for section in exam.sections:
            print(f"    - Section {section.number}: {section.title} ({len(section.questions)} questions)")
    except Exception as e:
        print(f"\n✗ Error creating ExamDocument: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Save extracted JSON
    output_json_path = "extracted_exam.json"
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(exam_data, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved extracted JSON to {output_json_path}")
    
    # Generate Word document
    output_docx_path = "extracted_exam.docx"
    try:
        # Try to remove existing file if it exists and is locked
        import time
        if os.path.exists(output_docx_path):
            try:
                os.remove(output_docx_path)
                time.sleep(0.1)  # Brief pause to ensure file is released
            except PermissionError:
                print(f"\n⚠ Warning: {output_docx_path} is open in another program.")
                print("   Please close it and try again, or the file will be saved with a timestamp.")
                # Use timestamped filename as fallback
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_docx_path = f"extracted_exam_{timestamp}.docx"
        
        build_exam_docx(output_docx_path, exam_data=exam)
        print(f"✓ Generated Word document: {output_docx_path}")
    except Exception as e:
        print(f"\n✗ Error generating document: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "="*60)
    print("✓ SUCCESS! Exam extraction and document generation complete.")
    print("="*60)


if __name__ == "__main__":
    main()
