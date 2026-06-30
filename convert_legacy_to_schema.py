"""
Utility script to convert legacy CONTENT format to new ExamDocument schema.

This helps migrate existing hardcoded content to the standardized format.
"""
from exam_schema import ExamDocument, ExamMetadata, ExamSection, ExamQuestion, ExamOption
from template import CONTENT
import re


def parse_legacy_content(content_list):
    """
    Parse legacy CONTENT format and convert to ExamDocument.
    
    This is a helper function to migrate existing hardcoded content.
    """
    exam_doc = ExamDocument(title="", metadata=ExamMetadata(), sections=[])
    
    current_section = None
    current_question = None
    
    for text, style_name, alignment_int, tabs in content_list:
        if style_name == 'ExamTitle':
            exam_doc.title = text
            
        elif style_name == 'ExamMeta':
            # Parse metadata lines
            # Format: "Sub:Science\tFM: 50" or "Class: 6\tTime: 1.30 hrs\tPM: 20"
            if 'Sub:' in text:
                match = re.search(r'Sub:([^\t]+)', text)
                if match:
                    exam_doc.metadata.subject = match.group(1).strip()
                match = re.search(r'FM:\s*(\d+)', text)
                if match:
                    exam_doc.metadata.full_marks = match.group(1)
            
            if 'Class:' in text:
                match = re.search(r'Class:\s*([^\t]+)', text)
                if match:
                    exam_doc.metadata.class_level = match.group(1).strip()
                match = re.search(r'Time:\s*([^\t]+)', text)
                if match:
                    exam_doc.metadata.time = match.group(1).strip()
                match = re.search(r'PM:\s*(\d+)', text)
                if match:
                    exam_doc.metadata.pass_marks = match.group(1)
                    
        elif style_name == 'ExamSectionHeader':
            # Save previous section if exists
            if current_section:
                exam_doc.sections.append(current_section)
            
            # Parse section header: "1. Multiple Choice Questions. (10*1=10)"
            match = re.match(r'(\d+)\.\s*(.+?)(?:\s*\(([^)]+)\))?\.?$', text)
            if match:
                number = match.group(1)
                title = match.group(2).strip()
                scoring = match.group(3) if match.group(3) else None
                if scoring:
                    scoring = f"({scoring})"
                
                current_section = ExamSection(
                    number=number,
                    title=title,
                    scoring=scoring,
                    questions=[]
                )
                current_question = None
                
        elif style_name == 'ExamQuestion':
            # Save previous question if exists
            if current_question and current_section:
                current_section.questions.append(current_question)
            
            # Parse question: "a. Where do we live?"
            match = re.match(r'^([a-z0-9]+)\.\s*(.+)$', text, re.IGNORECASE)
            if match:
                label = match.group(1)
                question_text = match.group(2).strip()
                current_question = ExamQuestion(
                    label=label,
                    text=question_text,
                    options=None  # Will be set if next line is ExamOption
                )
                
        elif style_name == 'ExamOption':
            # Parse options: "i. crust\tii. mantle\tiii. outer core\tiv. inner core"
            if current_question:
                options = []
                # Split by tab and parse each option
                option_parts = text.split('\t')
                for part in option_parts:
                    match = re.match(r'^([ivxlcdm]+|[a-z])\.\s*(.+)$', part.strip(), re.IGNORECASE)
                    if match:
                        opt_label = match.group(1)
                        opt_text = match.group(2).strip()
                        options.append(ExamOption(label=opt_label, text=opt_text))
                
                if options:
                    current_question.options = options
    
    # Don't forget the last question and section
    if current_question and current_section:
        current_section.questions.append(current_question)
    if current_section:
        exam_doc.sections.append(current_section)
    
    return exam_doc


if __name__ == "__main__":
    print("Converting legacy CONTENT to ExamDocument schema...")
    exam = parse_legacy_content(CONTENT)
    
    print(f"\nConverted Exam:")
    print(f"Title: {exam.title}")
    print(f"Subject: {exam.metadata.subject}")
    print(f"Full Marks: {exam.metadata.full_marks}")
    print(f"Class: {exam.metadata.class_level}")
    print(f"Time: {exam.metadata.time}")
    print(f"Pass Marks: {exam.metadata.pass_marks}")
    print(f"Number of sections: {len(exam.sections)}")
    
    for section in exam.sections:
        print(f"\nSection {section.number}: {section.title}")
        print(f"  Questions: {len(section.questions)}")
        for q in section.questions[:2]:  # Show first 2 questions
            print(f"    {q.label}. {q.text[:50]}...")
            if q.options:
                print(f"      Options: {len(q.options)}")
    
    # Save to JSON
    json_output = exam.to_json(indent=2)
    with open("converted_exam.json", "w", encoding="utf-8") as f:
        f.write(json_output)
    print(f"\n✓ Saved converted exam to converted_exam.json")
    
    # Test round-trip: JSON -> ExamDocument -> Document
    print("\nTesting round-trip conversion...")
    exam2 = ExamDocument.from_json(json_output)
    from template import build_exam_docx
    build_exam_docx("converted_test.docx", exam_data=exam2)
    print("✓ Generated converted_test.docx from converted JSON")

