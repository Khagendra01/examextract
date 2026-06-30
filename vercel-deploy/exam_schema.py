"""
Standardized schema for exam data extraction and formatting.

This schema defines the structure that AI models should extract from raw text/images.
The extracted data can then be converted to the format required by template.py.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json


@dataclass
class ExamMetadata:
    """Metadata about the exam (header information)."""
    subject: Optional[str] = None  # e.g., "Science"
    full_marks: Optional[str] = None  # e.g., "50" or "FM: 50"
    class_level: Optional[str] = None  # e.g., "6" or "Class: 6"
    time: Optional[str] = None  # e.g., "1.30 hrs" or "Time: 1.30 hrs"
    pass_marks: Optional[str] = None  # e.g., "20" or "PM: 20"
    
    def to_meta_lines(self) -> List[str]:
        """Convert metadata to formatted lines for the document."""
        lines = []
        if self.subject and self.full_marks:
            lines.append(f"Sub:{self.subject}\tFM: {self.full_marks}")
        if self.class_level and self.time and self.pass_marks:
            lines.append(f"Class: {self.class_level}\tTime: {self.time}\tPM: {self.pass_marks}")
        elif self.class_level and self.time:
            lines.append(f"Class: {self.class_level}\tTime: {self.time}")
        elif self.class_level:
            lines.append(f"Class: {self.class_level}")
        return lines


@dataclass
class ExamOption:
    """Multiple choice option."""
    label: str  # e.g., "i", "ii", "iii", "iv"
    text: str  # e.g., "crust", "mantle", etc.
    
    def format(self) -> str:
        """Format option as it appears in the document."""
        return f"{self.label}. {self.text}"


@dataclass
class ExamQuestion:
    """A single exam question."""
    label: str  # e.g., "a", "b", "c", "1", "2", etc.
    text: str  # The question text
    options: Optional[List[ExamOption]] = None  # For multiple choice questions
    sub_questions: Optional[List['ExamQuestion']] = None  # For questions with sub-parts (a, b, i, ii, etc.)
    nueva: Optional[Dict[str, Any]] = None  # For unknown/novel content types that don't fit standard structure
    
    def format_question(self) -> str:
        """Format question text with label."""
        return f"{self.label}. {self.text}"
    
    def format_options(self) -> Optional[str]:
        """Format options as a single line separated by tabs."""
        if not self.options:
            return None
        return "\t".join(opt.format() for opt in self.options)


@dataclass
class ExamSection:
    """A section of the exam (e.g., Multiple Choice, Short Answer, etc.)."""
    number: str  # e.g., "1", "2", "3"
    title: str  # e.g., "Multiple Choice Questions"
    scoring: Optional[str] = None  # e.g., "(10*1=10)" or "10*1=10"
    questions: List[ExamQuestion] = field(default_factory=list)
    nueva: Optional[Dict[str, Any]] = None  # For unknown/novel content types that don't fit standard structure
    
    def format_header(self) -> str:
        """Format section header."""
        if self.title:
            if self.scoring:
                return f"{self.number}. {self.title}. {self.scoring}"
            return f"{self.number}. {self.title}"
        else:
            # No title - just use number and scoring if available
            if self.scoring:
                return f"{self.number}. {self.scoring}"
            return f"{self.number}."


@dataclass
class ExamDocument:
    """Complete exam document structure."""
    title: str  # e.g., "Third Terminal Examination 2082"
    metadata: ExamMetadata = field(default_factory=ExamMetadata)
    instructions: Optional[str] = None  # e.g., "Attempt the questions.", "Answer all questions."
    sections: List[ExamSection] = field(default_factory=list)
    nueva: Optional[Dict[str, Any]] = None  # For unknown/novel content types that don't fit standard structure
    
    def to_content_format(self) -> List[tuple]:
        """
        Convert to the CONTENT format expected by template.py.
        
        Returns list of tuples: (text, style_name, alignment_int, tabs)
        """
        content = []
        
        # Title (centered)
        content.append((self.title, 'ExamTitle', 1, []))
        
        # Metadata lines
        meta_lines = self.metadata.to_meta_lines()
        for i, line in enumerate(meta_lines):
            if i == 0:
                # First meta line: Sub and FM
                tabs = [(6941, 'RIGHT')]
            elif i == 1:
                # Second meta line: Class, Time, PM
                tabs = [(3341, 'CENTER'), (6941, 'RIGHT')]
            else:
                tabs = []
            content.append((line, 'ExamMeta', None, tabs))
        
        # Instructions (if present)
        if self.instructions:
            content.append((self.instructions, 'Normal', 1, []))  # Centered
        
        # Separator line
        content.append(('*******************************************************************', 'Normal', None, []))
        
        # Sections and questions
        for section in self.sections:
            # Section header
            content.append((section.format_header(), 'ExamSectionHeader', None, []))
            
            # Questions in this section
            for question in section.questions:
                # Question text
                content.append((question.format_question(), 'ExamQuestion', None, []))
                
                # Sub-questions (if any) - render them as separate questions
                if question.sub_questions:
                    for sub_q in question.sub_questions:
                        content.append((sub_q.format_question(), 'ExamQuestion', None, []))
                        if sub_q.options:
                            options_text = sub_q.format_options()
                            if options_text:
                                content.append((options_text, 'ExamOption', None, []))
                
                # Options (if any)
                if question.options:
                    options_text = question.format_options()
                    if options_text:
                        content.append((options_text, 'ExamOption', None, []))
        
        return content
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "metadata": {
                "subject": self.metadata.subject,
                "full_marks": self.metadata.full_marks,
                "class_level": self.metadata.class_level,
                "time": self.metadata.time,
                "pass_marks": self.metadata.pass_marks,
            },
            "instructions": self.instructions,
            "nueva": self.nueva,
            "sections": [
                {
                    "number": section.number,
                    "title": section.title,
                    "scoring": section.scoring,
                    "nueva": section.nueva,
                    "questions": [
                        {
                            "label": q.label,
                            "text": q.text,
                            "options": [
                                {"label": opt.label, "text": opt.text}
                                for opt in (q.options or [])
                            ] if q.options else None,
                            "sub_questions": [
                                {
                                    "label": sq.label,
                                    "text": sq.text,
                                    "options": [
                                        {"label": opt.label, "text": opt.text}
                                        for opt in (sq.options or [])
                                    ] if sq.options else None,
                                    "nueva": sq.nueva
                                }
                                for sq in (q.sub_questions or [])
                            ] if q.sub_questions else None,
                            "nueva": q.nueva
                        }
                        for q in section.questions
                    ]
                }
                for section in self.sections
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExamDocument':
        """Create ExamDocument from dictionary."""
        metadata = ExamMetadata(
            subject=data.get("metadata", {}).get("subject"),
            full_marks=data.get("metadata", {}).get("full_marks"),
            class_level=data.get("metadata", {}).get("class_level"),
            time=data.get("metadata", {}).get("time"),
            pass_marks=data.get("metadata", {}).get("pass_marks"),
        )
        
        sections = []
        for sec_data in data.get("sections", []):
            questions = []
            for q_data in sec_data.get("questions", []):
                options = None
                if q_data.get("options"):
                    options = [
                        ExamOption(label=opt["label"], text=opt["text"])
                        for opt in q_data["options"]
                    ]
                
                sub_questions = None
                if q_data.get("sub_questions"):
                    sub_questions = []
                    for sq_data in q_data["sub_questions"]:
                        sq_options = None
                        if sq_data.get("options"):
                            sq_options = [
                                ExamOption(label=opt["label"], text=opt["text"])
                                for opt in sq_data["options"]
                            ]
                        sub_questions.append(ExamQuestion(
                            label=sq_data["label"],
                            text=sq_data["text"],
                            options=sq_options,
                            nueva=sq_data.get("nueva")
                        ))
                
                questions.append(ExamQuestion(
                    label=q_data["label"],
                    text=q_data["text"],
                    options=options,
                    sub_questions=sub_questions,
                    nueva=q_data.get("nueva")
                ))
            
            sections.append(ExamSection(
                number=sec_data["number"],
                title=sec_data["title"],
                scoring=sec_data.get("scoring"),
                questions=questions,
                nueva=sec_data.get("nueva")
            ))
        
        return cls(
            title=data["title"],
            metadata=metadata,
            instructions=data.get("instructions"),
            sections=sections,
            nueva=data.get("nueva")
        )
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ExamDocument':
        """Create ExamDocument from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


# Example usage and schema documentation
EXAMPLE_SCHEMA = {
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
                    "options": None
                },
                {
                    "label": "b",
                    "text": "Name the coldest planet of the solar system.",
                    "options": None
                }
            ]
        }
    ]
}

