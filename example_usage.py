"""
Example usage of the standardized exam schema and template.

This demonstrates how to:
1. Create exam data from structured format (what AI models should extract)
2. Convert to document format
3. Use with template.py
"""
from exam_schema import ExamDocument, ExamMetadata, ExamSection, ExamQuestion, ExamOption
from template import build_exam_docx
import json

# Example 1: Create exam data programmatically
def create_exam_example():
    """Create an exam document from structured data."""
    exam = ExamDocument(
        title="Third Terminal Examination 2082",
        metadata=ExamMetadata(
            subject="Science",
            full_marks="50",
            class_level="6",
            time="1.30 hrs",
            pass_marks="20"
        ),
        instructions="Attempt the questions.",
        sections=[
            ExamSection(
                number="1",
                title="Multiple Choice Questions",
                scoring="(10*1=10)",
                questions=[
                    ExamQuestion(
                        label="a",
                        text="Where do we live?",
                        options=[
                            ExamOption(label="i", text="crust"),
                            ExamOption(label="ii", text="mantle"),
                            ExamOption(label="iii", text="outer core"),
                            ExamOption(label="iv", text="inner core")
                        ]
                    ),
                    ExamQuestion(
                        label="b",
                        text="Which of the following is a magnetic substances?",
                        options=[
                            ExamOption(label="i", text="Iron"),
                            ExamOption(label="ii", text="wood"),
                            ExamOption(label="iii", text="plastic"),
                            ExamOption(label="iv", text="rubber")
                        ]
                    )
                ]
            ),
            ExamSection(
                number="2",
                title="Very short answer questions",
                scoring="(10*1=10)",
                questions=[
                    ExamQuestion(label="a", text="Define top soil.", options=None),
                    ExamQuestion(label="b", text="Name the coldest planet of the solar system.", options=None)
                ]
            )
        ]
    )
    return exam


# Example 2: Load from JSON (what AI models should output)
def load_from_json_example():
    """Load exam data from JSON string (typical AI extraction output)."""
    json_data = """
    {
        "title": "Third Terminal Examination 2082",
        "metadata": {
            "subject": "Science",
            "full_marks": "50",
            "class_level": "6",
            "time": "1.30 hrs",
            "pass_marks": "20"
        },
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
                    }
                ]
            }
        ]
    }
    """
    exam = ExamDocument.from_json(json_data)
    return exam


# Example 3: Save to JSON (for AI model reference)
def save_schema_example():
    """Save example schema as JSON for AI model reference."""
    exam = create_exam_example()
    json_output = exam.to_json(indent=2)
    print("Example JSON schema for AI models:")
    print(json_output)
    
    # Save to file
    with open("exam_schema_example.json", "w", encoding="utf-8") as f:
        f.write(json_output)
    print("\nSaved to exam_schema_example.json")


# Example 4: Generate document from structured data
def generate_document_example():
    """Generate .docx file from structured exam data."""
    # Method 1: From ExamDocument object
    exam = create_exam_example()
    build_exam_docx("output_from_schema.docx", exam_data=exam)
    print("Generated output_from_schema.docx from ExamDocument")
    
    # Method 2: From JSON string (typical AI workflow)
    json_data = load_from_json_example()
    build_exam_docx("output_from_json.docx", exam_data=json_data)
    print("Generated output_from_json.docx from JSON")


if __name__ == "__main__":
    print("=" * 60)
    print("Example 1: Create exam programmatically")
    print("=" * 60)
    exam1 = create_exam_example()
    print(f"Created exam: {exam1.title}")
    print(f"Number of sections: {len(exam1.sections)}")
    
    print("\n" + "=" * 60)
    print("Example 2: Load from JSON")
    print("=" * 60)
    exam2 = load_from_json_example()
    print(f"Loaded exam: {exam2.title}")
    
    print("\n" + "=" * 60)
    print("Example 3: Save schema example")
    print("=" * 60)
    save_schema_example()
    
    print("\n" + "=" * 60)
    print("Example 4: Generate documents")
    print("=" * 60)
    generate_document_example()

