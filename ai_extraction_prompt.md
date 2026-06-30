# AI Model Extraction Prompt

Use this prompt when asking AI models (like GPT-4, Claude, etc.) to extract exam data from raw text or images.

## Prompt Template

```
You are an expert at extracting structured data from exam documents. Extract the following information from the provided exam document and format it as JSON.

EXTRACTION REQUIREMENTS:

1. **Exam Title**: Extract the main title of the exam (e.g., "Third Terminal Examination 2082")

2. **Metadata**: Extract header information:
   - Subject (Sub): The subject name (e.g., "Science", "Mathematics")
   - Full Marks (FM): Total marks for the exam (e.g., "50", "100")
   - Class: Class/grade level (e.g., "6", "10")
   - Time: Duration of exam (e.g., "1.30 hrs", "2 hours")
   - Pass Marks (PM): Minimum passing marks (e.g., "20", "40")

3. **Instructions**: Extract any instruction lines that appear between the metadata and questions (e.g., "Attempt the questions.", "Answer all questions.", "Read carefully before answering."). These are usually centered or prominent text that gives general instructions.

4. **Sections**: For each section in the exam, extract:
   - Section Number: The section number (e.g., "1", "2", "3")
   - Section Title: The section name (e.g., "Multiple Choice Questions", "Short Answer Questions")
   - Scoring: Scoring format if mentioned (e.g., "(10*1=10)", "7x2=14")
   - Questions: For each question in the section:
     - Question Label: The question identifier (e.g., "a", "b", "c", "1", "2")
     - Question Text: The full question text
     - Options: If it's a multiple choice question, extract all options:
       - Option Label: The option identifier (e.g., "i", "ii", "iii", "iv", "A", "B", "C", "D")
       - Option Text: The option text
     - Nueva: For unknown/novel content types that don't fit standard structure (e.g., diagrams, special formatting, new question types), use this flexible field to store any JSON object

OUTPUT FORMAT:

Output the extracted data in this exact JSON format:

{
  "title": "Exam Title Here",
  "metadata": {
    "subject": "Subject Name",
    "full_marks": "Full Marks",
    "class_level": "Class/Grade",
    "time": "Time Duration",
    "pass_marks": "Pass Marks"
  },
  "instructions": "Instruction text like 'Attempt the questions.' (optional, can be null)",
  "sections": [
    {
      "number": "Section Number",
      "title": "Section Title",
      "scoring": "Scoring Format (optional)",
      "questions": [
        {
          "label": "Question Label",
          "text": "Question Text",
          "options": [
            {
              "label": "Option Label",
              "text": "Option Text"
            }
          ]
        }
      ]
    }
  ]
}

IMPORTANT NOTES:
- If a field is not found, use null (for optional fields) or omit it
- For non-multiple-choice questions, set "options" to null
- All text values should be strings (even numbers like "50" for marks)
- Preserve the exact text as it appears in the document
- Section numbers and question labels can be any format (numbers, letters, roman numerals, etc.)
- If scoring format is not explicitly mentioned, you can omit it or infer it from context
- **Handling Unknown Content Types**: If you encounter content that doesn't fit the standard structure (diagrams, tables, special formatting, new question types), use the "nueva" field instead of forcing it into incorrect structures. This prevents overfitting and allows for future schema extensions.

Now extract the exam data from the following document:

[PASTE EXAM DOCUMENT TEXT OR IMAGE DESCRIPTION HERE]
```

## Example Usage

### For Text Input:
```
[Use the prompt above, then paste the exam text]
```

### For Image Input:
```
[Use the prompt above, then describe the image or use vision capabilities]

Example: "Extract exam data from this image: [image attached]"
```

## Validation Checklist

After extraction, verify:
- [ ] Title is extracted correctly
- [ ] All metadata fields that are present are extracted
- [ ] All sections are included
- [ ] All questions within each section are included
- [ ] Multiple choice options are properly formatted (if applicable)
- [ ] Question labels and section numbers are preserved
- [ ] JSON is valid and properly formatted

## Common Issues and Solutions

1. **Missing Options**: If a question appears to be multiple choice but options aren't extracted, check if they're on separate lines or formatted differently.

2. **Incorrect Labels**: Question labels might be in different formats (a, b, c vs 1, 2, 3). Preserve the original format.

3. **Scoring Format**: Scoring might be written as "(10*1=10)" or "10×1=10" or "10 marks each". Extract as written.

4. **Metadata Variations**: Subject might be written as "Sub:", "Subject:", or just the subject name. Extract the value part.

5. **Section Titles**: Section titles might include the number or not. Extract the full title as written.

## Testing

After extraction, test the JSON by:
1. Loading it using `ExamDocument.from_json(json_string)`
2. Converting to document: `build_exam_docx("test.docx", exam_data=exam)`
3. Verify the output matches the original document structure

