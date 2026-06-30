# Exam Document Schema and Pipeline

This document describes the standardized schema for extracting exam data from raw text/images and converting it to formatted Word documents.

## Overview

The pipeline consists of three main components:

1. **`exam_schema.py`** - Defines the standardized data structure
2. **`template.py`** - Converts structured data to Word document format
3. **AI Extraction** - Extract structured data from raw text/images

## Schema Structure

### ExamDocument (Root)
- `title` (str): Exam title (e.g., "Third Terminal Examination 2082")
- `metadata` (ExamMetadata): Header information
- `instructions` (str, optional): Instruction lines (e.g., "Attempt the questions.", "Answer all questions.")
- `sections` (List[ExamSection]): List of exam sections

### ExamMetadata
- `subject` (str, optional): Subject name (e.g., "Science")
- `full_marks` (str, optional): Full marks (e.g., "50")
- `class_level` (str, optional): Class/grade (e.g., "6")
- `time` (str, optional): Time duration (e.g., "1.30 hrs")
- `pass_marks` (str, optional): Pass marks (e.g., "20")

### ExamSection
- `number` (str): Section number (e.g., "1", "2")
- `title` (str): Section title (e.g., "Multiple Choice Questions")
- `scoring` (str, optional): Scoring format (e.g., "(10*1=10)")
- `questions` (List[ExamQuestion]): List of questions in this section

### ExamQuestion
- `label` (str): Question label (e.g., "a", "b", "1", "2")
- `text` (str): Question text
- `options` (List[ExamOption], optional): Multiple choice options (if applicable)

### ExamOption
- `label` (str): Option label (e.g., "i", "ii", "iii", "iv")
- `text` (str): Option text

## JSON Schema Format

AI models should extract and output data in this JSON format:

```json
{
  "title": "Third Terminal Examination 2082",
  "metadata": {
    "subject": "Science",
    "full_marks": "50",
    "class_level": "6",
    "time": "1.30 hrs",
    "pass_marks": "20"
  },
  "instructions": "Attempt the questions.",
  "sections": [
    {
      "number": "1",
      "title": "Multiple Choice Questions",
      "scoring": "(10*1=10)",
      "questions": [
        {
          "label": "a",
          "text": "Where do we live?",
          "options": [
            {"label": "i", "text": "crust"},
            {"label": "ii", "text": "mantle"},
            {"label": "iii", "text": "outer core"},
            {"label": "iv", "text": "inner core"}
          ]
        },
        {
          "label": "b",
          "text": "Which of the following is a magnetic substances?",
          "options": [
            {"label": "i", "text": "Iron"},
            {"label": "ii", "text": "wood"},
            {"label": "iii", "text": "plastic"},
            {"label": "iv", "text": "rubber"}
          ]
        }
      ]
    },
    {
      "number": "2",
      "title": "Very short answer questions",
      "scoring": "(10*1=10)",
      "questions": [
        {
          "label": "a",
          "text": "Define top soil.",
          "options": null
        },
        {
          "label": "b",
          "text": "Name the coldest planet of the solar system.",
          "options": null
        }
      ]
    }
  ]
}
```

## Usage

### Method 1: From JSON (Recommended for AI Integration)

```python
from exam_schema import ExamDocument
from template import build_exam_docx

# AI model extracts data and outputs JSON
json_string = """{
  "title": "Exam Title",
  "metadata": {...},
  "sections": [...]
}"""

# Load and convert
exam = ExamDocument.from_json(json_string)
build_exam_docx("output.docx", exam_data=exam)
```

### Method 2: From Dictionary

```python
from exam_schema import ExamDocument
from template import build_exam_docx

data = {
    "title": "Exam Title",
    "metadata": {...},
    "sections": [...]
}

exam = ExamDocument.from_dict(data)
build_exam_docx("output.docx", exam_data=exam)
```

### Method 3: Programmatically

```python
from exam_schema import ExamDocument, ExamMetadata, ExamSection, ExamQuestion, ExamOption
from template import build_exam_docx

exam = ExamDocument(
    title="My Exam",
    metadata=ExamMetadata(subject="Math", full_marks="100"),
    sections=[
        ExamSection(
            number="1",
            title="Multiple Choice",
            questions=[
                ExamQuestion(
                    label="a",
                    text="What is 2+2?",
                    options=[
                        ExamOption(label="i", text="3"),
                        ExamOption(label="ii", text="4"),
                        ExamOption(label="iii", text="5")
                    ]
                )
            ]
        )
    ]
)

build_exam_docx("output.docx", exam_data=exam)
```

## AI Model Integration

### Prompt for AI Models

When asking an AI model to extract exam data, use this prompt:

```
Extract the following information from the exam document and format it as JSON:

1. Exam title
2. Metadata: Subject, Full Marks (FM), Class, Time, Pass Marks (PM)
3. Sections: For each section, extract:
   - Section number and title
   - Scoring format (if mentioned)
   - Questions: For each question, extract:
     - Question label (a, b, c, etc.)
     - Question text
     - Options (if multiple choice): label (i, ii, iii, iv) and text

Output the data in this exact JSON format:
{
  "title": "...",
  "metadata": {
    "subject": "...",
    "full_marks": "...",
    "class_level": "...",
    "time": "...",
    "pass_marks": "..."
  },
  "sections": [
    {
      "number": "...",
      "title": "...",
      "scoring": "...",
      "questions": [
        {
          "label": "...",
          "text": "...",
          "options": [
            {"label": "...", "text": "..."}
          ]
        }
      ]
    }
  ]
}
```

### Validation

The schema includes validation and conversion methods:
- `ExamDocument.to_json()` - Convert to JSON string
- `ExamDocument.from_json()` - Load from JSON string
- `ExamDocument.to_dict()` - Convert to Python dictionary
- `ExamDocument.from_dict()` - Load from dictionary
- `ExamDocument.to_content_format()` - Convert to legacy format (internal use)

## Field Mapping

| Field Name | Description | Example | Required |
|------------|-------------|---------|----------|
| `title` | Exam title | "Third Terminal Examination 2082" | Yes |
| `metadata.subject` | Subject name | "Science" | No |
| `instructions` | Instruction lines | "Attempt the questions." | No |
| `metadata.full_marks` | Full marks | "50" | No |
| `metadata.class_level` | Class/grade | "6" | No |
| `metadata.time` | Time duration | "1.30 hrs" | No |
| `metadata.pass_marks` | Pass marks | "20" | No |
| `sections[].number` | Section number | "1", "2" | Yes |
| `sections[].title` | Section title | "Multiple Choice Questions" | Yes |
| `sections[].scoring` | Scoring format | "(10*1=10)" | No |
| `sections[].questions[].label` | Question label | "a", "b", "1", "2" | Yes |
| `sections[].questions[].text` | Question text | "Where do we live?" | Yes |
| `sections[].questions[].options` | Multiple choice options | Array of {label, text} | No |
| `sections[].questions[].options[].label` | Option label | "i", "ii", "iii", "iv" | Yes (if options present) |
| `sections[].questions[].options[].text` | Option text | "crust", "mantle" | Yes (if options present) |

## Notes

- All text fields are strings (even numbers like "50" for marks)
- Options are only required for multiple choice questions
- Section numbers and question labels can be any string (not just numbers/letters)
- Scoring format is optional and can include any format string
- Missing metadata fields will be omitted from the output document

## Backward Compatibility

The original `CONTENT` format is still supported for backward compatibility:

```python
from template import build_exam_docx, CONTENT

# Legacy method
build_exam_docx("output.docx", content=CONTENT)
```

