import base64
import requests
import os
import sys
import re
from typing import List
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "xiaomi/mimo-v2.5"

PROMPT = """Extract exam content from the image(s) and output in this EXACT format:

T: [Exam Title]
M: Sub:[Subject]\tFM: [Full Marks]
M: Class: [Class]\tTime: [Time]\tPM: [Pass Marks]
R: ******************************************************
S: [Section Number]. [Section Title]. ([Scoring])
Q: [Question Label]. [Question Text]
O: [Option Label]. [Option Text]\t [Option Label]. [Option Text]...
P: [Prompt/Hint]
Q: [Next Question]...

FORMAT RULES:

1. T: Title - Exam title only

2. M: Metadata - TWO lines:
   Line 1: Sub:[Subject]\tFM: [Full Marks]
   Line 2: Class: [Class]\tTime: [Time]\tPM: [Pass Marks]
   Use "-" for missing: Time: - or PM: -

3. R: Separator - Use ONLY for the asterisk line: ******************************************************
   For other content that doesn't fit categories, also use R:

4. S: Section - Format: [Number]. [Title]. ([Scoring])
   - Use actual section titles (e.g., "Multiple Choice Questions", "Short Answer Questions")
   - If no title, use: S: 1. (-)
   - Scoring: (10*1=10) or (-) if none

5. Q: Question - Format: [Label]. [Question Text]
   - Use EXACT labels from document (1, 2, 3, a, b, c, etc.)
   - Include ALL question parts:
     * If question has sub-parts (a, b, i, ii), include them ALL in the Q: line
     * Example: "Q: 1. write the following in set notation. [2] a) 2 belongs to the set of natural number N b) 1/5 does not belong to the set N"
     * Example: "Q: 5. a) Factorise 20 and 30 separately [2] b) Find the product of common prime factors of 20 and 30 [1]"
   - Include marks like [2] in the text
   - Number ALL questions sequentially: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14...
   - DO NOT skip numbers (if you see 8 then 10, include Q: 9 even if empty)
   - DO NOT duplicate numbers

6. O: Options - Multiple choice only
   Format: [Label]. [Text]\t [Label]. [Text]\t ...
   Example: O: i. crust\t ii. mantle\t iii. outer core\t iv. inner core

7. P: Prompt - ONLY for hints/prompts in parentheses
   Example: P: (Write 2-3 sentences about...)
   DO NOT use P: for sub-questions

8. Instructions - If you see "Attempt the questions" or similar:
   - Include as part of section if section-specific
   - Otherwise, put under R: as a separate line

9. Missing/Unknown content - Use R: for anything that doesn't fit T/M/S/Q/O/P

CRITICAL: Extract EVERY question with ALL its parts. Do not skip or merge questions. Follow the exact numbering in the document.

Output ONLY the formatted text, no markdown, no code blocks, no explanations."""


def encode_image(image_path):
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_exam(image_paths):
    """Extract exam data from one or multiple images."""
    # Encode all images
    image_parts = []
    for img_path in image_paths:
        if not os.path.exists(img_path):
            print(f"Error: {img_path} not found!")
            return None
        
        mime_type = "image/jpeg" if img_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
        image_data = encode_image(img_path)
        image_parts.append({
            "inlineData": {
                "mimeType": mime_type,
                "data": image_data
            }
        })
    
    # Prepare API request (OpenRouter / OpenAI-compatible format)
    content_parts = [{"type": "text", "text": PROMPT}]
    for img_part in image_parts:
        # img_part is {"inlineData": {"mimeType": ..., "data": ...}}
        mime = img_part["inlineData"]["mimeType"]
        data = img_part["inlineData"]["data"]
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{data}"}
        })

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": content_parts}],
    }
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    print(f"Processing {len(image_paths)} image(s)...")
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: API request failed with status {response.status_code}")
        print(response.text)
        return None
    
    # Extract response text (OpenAI-compatible format)
    response_data = response.json()
    extracted_text = response_data["choices"][0]["message"]["content"]
    
    return extracted_text


def normalize_question_labels(text: str) -> str:
    """Convert question labels from ')' to '.' format (e.g., '1)' -> '1.')"""
    # Pattern to match question labels like "1)", "2)", etc. at the start of Q: lines
    # Also handle cases like "Q: 1) text" -> "Q: 1. text"
    pattern = r'^(Q:\s*)(\d+)\)\s*'
    return re.sub(pattern, r'\1\2. ', text, flags=re.MULTILINE)


def normalize_required_fields(text: str) -> str:
    """
    Ensure required fields are present:
    - T: line must always be present
    - M: lines should have placeholders for Sub:, Class:, Time:, FM:, PM: if missing
    """
    lines = text.strip().split("\n")
    normalized = []
    has_title = False
    meta_lines = []
    other_lines = []
    
    # Separate lines by type
    for line in lines:
        line = line.strip()
        if not line:
            continue
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
        text_content = meta_line[2:].strip()  # Remove "M: " prefix
        # Replace literal \t with a marker for easier parsing
        text_normalized = text_content.replace("\\t", "\t")
        
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
    
    return normalized_text


def main():
    # Get image paths from command line or use default
    if len(sys.argv) > 1:
        image_paths = sys.argv[1:]
    else:
        # Default to image.jpeg if no args
        image_paths = ["image.jpeg"]
    
    # Extract exam data
    output = extract_exam(image_paths)
    
    if output:
        # Normalize to ensure required fields are present
        output = normalize_required_fields(output)
        
        print("\n" + "="*60)
        print("Extracted Exam Content:")
        print("="*60)
        print(output)
        
        # Save to input.txt
        with open("input.txt", "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\n✓ Saved to input.txt")


if __name__ == "__main__":
    main()

