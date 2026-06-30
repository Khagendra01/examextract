import json
from exam_schema import ExamDocument

print("=" * 70)
print("IMAGE EXTRACTION VERIFICATION REPORT")
print("=" * 70)

# Load extracted JSON
with open('extracted_exam.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

exam = ExamDocument.from_dict(data)
questions = data["sections"][0]["questions"]

print("\n1. EXTRACTION SUMMARY:")
print(f"   - Title: {data['title']}")
print(f"   - Subject: {data['metadata']['subject']}")
print(f"   - Full Marks: {data['metadata']['full_marks']}")
print(f"   - Class Level: {data['metadata']['class_level']}")
print(f"   - Total Questions Extracted: {len(questions)}")

print("\n2. QUESTION SEQUENCE ANALYSIS:")
labels = [q["label"] for q in questions]
print(f"   - Question labels found: {labels}")
print(f"   - Expected sequence: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14")
print(f"   - Missing numbers: ", end="")
missing = []
for i in range(1, 15):
    if str(i) not in labels:
        missing.append(str(i))
if missing:
    print(f"{', '.join(missing)} [ISSUE: Questions missing from sequence]")
else:
    print("None [OK]")

print("\n3. QUESTION CONTENT VERIFICATION:")
print("   Checking each question for completeness...\n")

# Expected questions based on AI analysis notes
expected_questions = {
    "1": {
        "has_subquestions": True,
        "subquestion_count": 2,
        "subquestion_labels": ["a", "b"],
        "text_contains": "set notation"
    },
    "2": {
        "has_subquestions": False,
        "text_contains": "smallest number"
    },
    "3": {
        "has_subquestions": True,
        "subquestion_count": 2,
        "subquestion_labels": ["i", "ii"],
        "text_contains": "Rs 1500"
    },
    "4": {
        "has_subquestions": False,
        "text_contains": "prime numbers"
    },
    "5": {
        "has_subquestions": False,
        "text_contains": "l.c.m"
    },
    "6": {
        "has_subquestions": False,
        "text_contains": "square root"
    },
    "7": {
        "has_subquestions": False,
        "text_contains": "Larpa"
    },
    "8": {
        "has_subquestions": False,
        "text_contains": "bags"
    },
    "10": {
        "has_subquestions": True,
        "subquestion_count": 1,
        "subquestion_labels": ["a"],
        "text_contains": "Find the value"
    },
    "11": {
        "has_subquestions": True,
        "subquestion_count": 1,
        "subquestion_labels": ["a"],
        "text_contains": "simplify"
    },
    "12": {
        "has_subquestions": False,
        "text_contains": "mobile"
    },
    "13": {
        "has_subquestions": False,
        "text_contains": "apples"
    },
    "14": {
        "has_subquestions": True,
        "subquestion_count": 2,
        "subquestion_labels": ["i", "ii"],
        "text_contains": "height"
    }
}

issues_found = []
for q in questions:
    label = q["label"]
    if label in expected_questions:
        expected = expected_questions[label]
        actual_subqs = q.get("sub_questions")
        has_subqs = actual_subqs is not None and len(actual_subqs) > 0
        
        # Check sub-question structure
        if expected["has_subquestions"] != has_subqs:
            issues_found.append(f"Q{label}: Expected sub-questions: {expected['has_subquestions']}, Found: {has_subqs}")
        
        if expected["has_subquestions"] and has_subqs:
            if len(actual_subqs) != expected.get("subquestion_count", 0):
                issues_found.append(f"Q{label}: Expected {expected.get('subquestion_count')} sub-questions, found {len(actual_subqs)}")
            
            expected_labels = expected.get("subquestion_labels", [])
            actual_labels = [sq["label"] for sq in actual_subqs]
            if actual_labels != expected_labels:
                issues_found.append(f"Q{label}: Expected sub-question labels {expected_labels}, found {actual_labels}")
        
        # Check text content
        text_lower = q["text"].lower()
        if expected.get("text_contains") and expected["text_contains"].lower() not in text_lower:
            issues_found.append(f"Q{label}: Text doesn't contain expected keyword '{expected['text_contains']}'")
    else:
        issues_found.append(f"Q{label}: Unexpected question label (not in expected list)")

if issues_found:
    print("   ISSUES FOUND:")
    for issue in issues_found:
        print(f"     - {issue}")
else:
    print("   [OK] All questions match expected structure")

print("\n4. DETAILED QUESTION BREAKDOWN:")
for i, q in enumerate(questions, 1):
    print(f"\n   Question {q['label']}:")
    text_preview = q['text'][:60] + "..." if len(q['text']) > 60 else q['text']
    print(f"     Text: {text_preview}")
    if q.get("sub_questions"):
        print(f"     Sub-questions: {len(q['sub_questions'])}")
        for sq in q['sub_questions']:
            sq_preview = sq['text'][:50] + "..." if len(sq['text']) > 50 else sq['text']
            print(f"       {sq['label']}. {sq_preview}")
    else:
        print(f"     Sub-questions: None")

print("\n5. METADATA VERIFICATION:")
metadata = data["metadata"]
metadata_issues = []
if metadata["subject"].endswith("."):
    metadata_issues.append("Subject has trailing period")
if not metadata.get("time"):
    metadata_issues.append("Time is missing (may be OK if not in image)")
if not metadata.get("pass_marks"):
    metadata_issues.append("Pass marks is missing (may be OK if not in image)")

if metadata_issues:
    print("   Issues:")
    for issue in metadata_issues:
        print(f"     - {issue}")
else:
    print("   [OK] Metadata looks good")

print("\n6. STRUCTURE VALIDATION:")
try:
    content = exam.to_content_format()
    print(f"   [OK] Successfully converts to content format")
    print(f"   - Total content items: {len(content)}")
    
    # Check for proper formatting
    has_title = any(item[1] == 'ExamTitle' for item in content)
    has_meta = any(item[1] == 'ExamMeta' for item in content)
    has_section = any(item[1] == 'ExamSectionHeader' for item in content)
    has_questions = any(item[1] == 'ExamQuestion' for item in content)
    
    print(f"   - Has title: {has_title}")
    print(f"   - Has metadata: {has_meta}")
    print(f"   - Has section header: {has_section}")
    print(f"   - Has questions: {has_questions}")
except Exception as e:
    print(f"   [ERROR] Failed to convert: {e}")

print("\n7. NUEVA FIELD CHECK:")
nueva_ok = True
if "nueva" not in data:
    print("   [X] Document level nueva missing")
    nueva_ok = False
if "nueva" not in data["sections"][0]:
    print("   [X] Section level nueva missing")
    nueva_ok = False
if "nueva" not in questions[0]:
    print("   [X] Question level nueva missing")
    nueva_ok = False

if nueva_ok:
    print("   [OK] All nueva fields present (ready for unknown content types)")

print("\n" + "=" * 70)
print("VERIFICATION SUMMARY:")
print("=" * 70)

total_issues = len(issues_found) + len(metadata_issues) + (1 if '9' in missing else 0)
if total_issues == 0:
    print("\n[OK] Extraction appears to be CLEAR and ACCURATE!")
    print("     All questions extracted correctly with proper structure.")
else:
    print(f"\n[!] Found {total_issues} potential issue(s):")
    if '9' in missing:
        print("     - Question 9 is missing from sequence")
    if issues_found:
        print(f"     - {len(issues_found)} question structure/content issue(s)")
    if metadata_issues:
        print(f"     - {len(metadata_issues)} metadata issue(s)")
    print("\n     Review the detailed breakdown above for specifics.")

print("\n" + "=" * 70)



