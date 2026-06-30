import json
from exam_schema import ExamDocument
from collections import Counter

print("=" * 60)
print("JSON VERIFICATION REPORT")
print("=" * 60)

# Load JSON
with open('extracted_exam.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 1. Check nueva fields are present
print("\n1. NUEVA FIELD CHECK:")
print("   - Document nueva:", "[OK] Present" if "nueva" in data else "[X] Missing")
print("   - Section nueva:", "[OK] Present" if data["sections"][0].get("nueva") is not None else "[X] Missing")
print("   - Question nueva:", "[OK] Present" if data["sections"][0]["questions"][0].get("nueva") is not None else "[X] Missing")

# 2. Check structure
print("\n2. STRUCTURE CHECK:")
try:
    exam = ExamDocument.from_dict(data)
    print("   [OK] JSON loads into ExamDocument successfully")
    print(f"   - Title: {exam.title}")
    print(f"   - Subject: {exam.metadata.subject}")
    print(f"   - Sections: {len(exam.sections)}")
    print(f"   - Total Questions: {sum(len(s.questions) for s in exam.sections)}")
except Exception as e:
    print(f"   ✗ Error loading: {e}")

# 3. Check question labels
print("\n3. QUESTION LABEL ANALYSIS:")
questions = data["sections"][0]["questions"]
labels = [q["label"] for q in questions]
print(f"   - Question labels found: {labels}")
print(f"   - Total questions: {len(labels)}")
print(f"   - Missing question 9: {'[X] YES' if '9' not in labels else '[OK] NO'}")

# Check if labels are numeric vs alphabetic
numeric_labels = [l for l in labels if l.isdigit()]
alphabetic_labels = [l for l in labels if l.isalpha()]
print(f"   - Numeric labels: {len(numeric_labels)} ({numeric_labels[:5]}...)")
print(f"   - Alphabetic labels: {len(alphabetic_labels)} ({alphabetic_labels[:5] if alphabetic_labels else 'None'}...)")

# 4. Check metadata
print("\n4. METADATA CHECK:")
metadata = data["metadata"]
print(f"   - Subject: '{metadata['subject']}' {'[X] Has period' if metadata['subject'].endswith('.') else '[OK] Clean'}")
print(f"   - Full marks: {metadata['full_marks']}")
print(f"   - Class level: {metadata['class_level']}")
print(f"   - Time: {metadata['time']}")
print(f"   - Pass marks: {metadata['pass_marks']}")

# 5. Check section scoring
print("\n5. SECTION SCORING:")
section = data["sections"][0]
print(f"   - Scoring: {section.get('scoring', 'null')}")

# 6. Compare to originaltemplate.py format
print("\n6. COMPARISON TO ORIGINAL TEMPLATE:")
print("   Expected format from originaltemplate.py:")
print("   - Questions use letters: a, b, c, d, e, f, g, h, i, j...")
print("   - Each section resets to 'a'")
print("   - Current format:")
if numeric_labels:
    print(f"   [X] Uses numeric labels (1, 2, 3...) instead of letters")
    print(f"   -> Should convert to: a, b, c, d, e, f, g, h, i, j, k, l, m, n")
else:
    print("   [OK] Uses alphabetic labels")

# 7. Check sub-question structure
print("\n7. SUB-QUESTION STRUCTURE:")
sub_q_count = sum(1 for q in questions if q.get("sub_questions"))
print(f"   - Questions with sub-questions: {sub_q_count}")
for i, q in enumerate(questions[:3], 1):
    if q.get("sub_questions"):
        sq_labels = [sq["label"] for sq in q["sub_questions"]]
        print(f"   - Q{q['label']} has sub-questions: {sq_labels}")

# 8. Test conversion to content format
print("\n8. CONTENT FORMAT CONVERSION TEST:")
try:
    content = exam.to_content_format()
    print(f"   [OK] Converts to content format successfully")
    print(f"   - Total content items: {len(content)}")
    print(f"   - Sample items:")
    for i, (text, style, align, tabs) in enumerate(content[:5], 1):
        text_preview = text[:50] + "..." if len(text) > 50 else text
        print(f"     {i}. [{style}] {text_preview}")
except Exception as e:
    print(f"   [X] Error converting: {e}")
    import traceback
    traceback.print_exc()

# 9. Issues summary
print("\n" + "=" * 60)
print("ISSUES SUMMARY:")
print("=" * 60)
issues = []
if metadata['subject'].endswith('.'):
    issues.append("Subject has trailing period: 'math.' -> should be 'Math'")
if numeric_labels:
    issues.append(f"Questions use numeric labels instead of letters")
if '9' not in labels:
    issues.append("Question 9 is missing from sequence")
if not section.get('scoring'):
    issues.append("Section scoring is null (should have format like '(14*varies=50)')")

if issues:
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
else:
    print("  [OK] No major issues found!")

print("\n" + "=" * 60)

