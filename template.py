# pip install python-docx
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from typing import Optional, List
try:
    from exam_schema import ExamDocument
except ImportError:
    ExamDocument = None

# Legacy hardcoded content (for backward compatibility)
CONTENT = [('Third Terminal Examination 2082', 'ExamTitle', 1, []),
 ('Sub:Science\tFM: 50', 'ExamMeta', None, [(6941, 'RIGHT')]),
 ('Class: 6\tTime: 1.30 hrs\tPM: 20', 'ExamMeta', None, [(3341, 'CENTER'), (6941, 'RIGHT')]),
 ('*******************************************************************', 'Normal', None, []),
 ('1. Multiple Choice Questions. (10*1=10)', 'ExamSectionHeader', None, []),
 ('a. Where do we live?', 'ExamQuestion', None, []),
 ('i. crust\tii. mantle\tiii. outer core\tiv. inner core', 'ExamOption', None, []),
 ('b. Which of the following is a magnetic substances?', 'ExamQuestion', None, []),
 ('i. Iron\tii. wood\tiii. plastic\tiv. rubber', 'ExamOption', None, []),
 ('c. Which is a heating element?', 'ExamQuestion', None, []),
 ('i. nichrome\tii.copper\tiii. iron\tiv. aluminium', 'ExamOption', None, []),
 ('d. This layer is the innermost layer of the earth.', 'ExamQuestion', None, []),
 ('i. Crust\tii. Mantle\tiii. Outer core\tiv. inner core', 'ExamOption', None, []),
 ('e. Which of the following is a natural magnet?', 'ExamQuestion', None, []),
 ('i. lodestone\tii. bar magnetic\tiii. u-shaped magnet\tiv. horse shoe magnet', 'ExamOption', None, []),
 ('f. Which is a rechargeable cell?', 'ExamQuestion', None, []),
 ('i. accumulator\tii. simple cell\tiii. primary cell\tiv.load', 'ExamOption', None, []),
 ('g. Which of the following is not a part of the solar system?', 'ExamQuestion', None, []),
 ('i. galaxy\tii. earth\tiii. sun\tiv. satelite', 'ExamOption', None, []),
 ('h. Which of the following uses electromagnet?', 'ExamQuestion', None, []),
 ('i. electric bell\tii. plastic\tiii. wood\tiv. zinc', 'ExamOption', None, []),
 ('i. Which device defects a small amount of electricity?', 'ExamQuestion', None, []),
 ('i. galvanometer\tii. fuse\tiii. MCB\tiv. volt', 'ExamOption', None, []),
 ('j. What is the SI unit of current electricity?', 'ExamQuestion', None, []),
 ('i Ampere\tii. newton\tiii. pascal\tiv. joule', 'ExamOption', None, []),
 ('2. Very short answer questions. (10*1=10)', 'ExamSectionHeader', None, []),
 ('a. Define top soil.', 'ExamQuestion', None, []),
 ('b. Name the coldest planet of the solar system.', 'ExamQuestion', None, []),
 ('c. What is the SI unit of current electricity?', 'ExamQuestion', None, []),
 ('d. Which metal acts as a negative terminal in the simple cell?', 'ExamQuestion', None, []),
 ('e. List one preventive measures of soil pollution.', 'ExamQuestion', None, []),
 ('f. Show any one difference between sun and planet in a table.', 'ExamQuestion', None, []),
 ('g. A rubber band cannot pulled by a magnet. Why?', 'ExamQuestion', None, []),
 ('h. Write down the methods of magnetization.', 'ExamQuestion', None, []),
 ('i. What do you mean by magnetism?', 'ExamQuestion', None, []),
 ('j. Mention the types of weathering.', 'ExamQuestion', None, []),
 ('3. Short question answer. (7x2=14)', 'ExamSectionHeader', None, []),
 ('a. Terrace farming is done in the hilly region, why?', 'ExamQuestion', None, []),
 ('b. Write any two difference between open circuit and closed circuit.', 'ExamQuestion', None, []),
 ('c. Define north pole and south pole.', 'ExamQuestion', None, []),
 ('d. Why load does not work in an open circuit?', 'ExamQuestion', None, []),
 ('e. Draw a well labelled diagram of a bar magnet and magnetic field around it.', 'ExamQuestion', None, []),
 ('f. List any four causes of soil erosion.', 'ExamQuestion', None, []),
 ('g. Write the name of six seasons with their tentative Nepali months.', 'ExamQuestion', None, []),
 ('4. Long questions. (4x4=16)', 'ExamSectionHeader', None, []),
 ('a. Define solar system. List the name of eight planets and describe any two of them.', 'ExamQuestion', None, []),
 ('b. Draw a well labelled diagram of open circuit and closed circuit.', 'ExamQuestion', None, []),
 ('c. Write two differences between simple cell and dry cell.', 'ExamQuestion', None, []),
 ('Nichrome produces a large amount of heat energy. why?', 'ExamQuestion', None, []),
 ('d. Describe single touch method of making a magnet with the help of diagram.', 'ExamQuestion', None, [])]


def _set_style_font(style, font_name: str):
    """
    Ensure Times New Roman applies for all character sets (ascii/hAnsi/eastAsia/cs).
    """
    style.font.name = font_name
    rPr = style._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:eastAsia"), font_name)
    rFonts.set(qn("w:cs"), font_name)


def _set_columns(section, num=2, space_twips=260, sep=True):
    """
    python-docx doesn't expose a high-level API for columns, so we set the sectPr XML.
    """
    sectPr = section._sectPr
    cols = sectPr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        sectPr.append(cols)
    cols.set(qn("w:num"), str(num))
    cols.set(qn("w:space"), str(space_twips))
    if sep:
        cols.set(qn("w:sep"), "1")
    elif qn("w:sep") in cols.attrib:
        del cols.attrib[qn("w:sep")]


def build_exam_docx(output_path: str, exam_data=None, content: Optional[List[tuple]] = None):
    """
    Build exam document from structured data or legacy content format.
    
    Args:
        output_path: Path to save the output .docx file
        exam_data: ExamDocument object (preferred method - from exam_schema)
        content: Legacy content format list of tuples (for backward compatibility)
    
    Usage:
        # Method 1: Using structured ExamDocument (recommended)
        exam = ExamDocument.from_json(json_string)
        build_exam_docx("output.docx", exam_data=exam)
        
        # Method 2: Using legacy content format
        build_exam_docx("output.docx", content=CONTENT)
    """
    # Convert ExamDocument to content format if provided
    if exam_data:
        content = exam_data.to_content_format()
    elif content is None:
        # Default to legacy CONTENT
        content = CONTENT
    
    doc = Document()

    # --- Page setup: A4 landscape, compact margins ---
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Cm(29.7)   # A4 landscape width
    section.page_height = Cm(21.0)  # A4 landscape height

    # ~1cm margins (compact like the sample)
    section.top_margin = Cm(1)
    section.bottom_margin = Cm(1)
    section.left_margin = Cm(1)
    section.right_margin = Cm(1)

    # Two columns with a separator line
    _set_columns(section, num=2, space_twips=260, sep=True)

    # --- Base style: Times New Roman, very compact spacing ---
    normal = doc.styles["Normal"]
    _set_style_font(normal, "Times New Roman")
    normal.font.size = Pt(13)
    normal.font.bold = False
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    normal.paragraph_format.line_spacing = Pt(14)

    # --- Custom styles to match the sample ---
    st_title = doc.styles.add_style("ExamTitle", 1)  # 1 = paragraph style
    _set_style_font(st_title, "Times New Roman")
    st_title.font.size = Pt(16)
    st_title.font.bold = True
    st_title.paragraph_format.space_before = Pt(0)
    st_title.paragraph_format.space_after = Pt(0)
    st_title.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    st_title.paragraph_format.line_spacing = Pt(18)

    st_meta = doc.styles.add_style("ExamMeta", 1)
    _set_style_font(st_meta, "Times New Roman")
    st_meta.font.size = Pt(14)
    st_meta.font.bold = False
    st_meta.paragraph_format.left_indent = Pt(17)
    st_meta.paragraph_format.space_before = Pt(0)
    st_meta.paragraph_format.space_after = Pt(0)
    st_meta.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    st_meta.paragraph_format.line_spacing = Pt(13)

    st_section = doc.styles.add_style("ExamSectionHeader", 1)
    _set_style_font(st_section, "Times New Roman")
    st_section.font.size = Pt(14)
    st_section.font.bold = False
    st_section.paragraph_format.space_before = Pt(4)
    st_section.paragraph_format.space_after = Pt(0)
    st_section.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    st_section.paragraph_format.line_spacing = Pt(13)

    st_q = doc.styles.add_style("ExamQuestion", 1)
    _set_style_font(st_q, "Times New Roman")
    st_q.font.size = Pt(13)
    st_q.font.bold = False
    st_q.paragraph_format.left_indent = Pt(11.35)
    st_q.paragraph_format.space_before = Pt(0.5)
    st_q.paragraph_format.space_after = Pt(0.5)
    st_q.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    st_q.paragraph_format.line_spacing = Pt(14)

    st_opt = doc.styles.add_style("ExamOption", 1)
    _set_style_font(st_opt, "Times New Roman")
    st_opt.font.size = Pt(13)
    st_opt.font.bold = False
    st_opt.paragraph_format.left_indent = Pt(22.7)
    st_opt.paragraph_format.space_before = Pt(0.5)
    st_opt.paragraph_format.space_after = Pt(0.5)
    st_opt.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    st_opt.paragraph_format.line_spacing = Pt(14)

    # --- Write content to document ---
    for text, style_name, alignment_int, tabs in content:
        p = doc.add_paragraph(text, style=style_name)

        # Paragraph alignment (only used for the main title in this doc)
        if alignment_int is not None:
            p.alignment = WD_ALIGN_PARAGRAPH(alignment_int)

        # Custom tab stops for the meta lines
        if tabs:
            p.paragraph_format.tab_stops.clear_all()
            for pos_twips, align_name in tabs:
                align_enum = getattr(WD_TAB_ALIGNMENT, align_name)
                # 1 point = 20 twips, so Pt(pos_twips/20) preserves the exact position
                p.paragraph_format.tab_stops.add_tab_stop(Pt(pos_twips / 20.0), alignment=align_enum)

    doc.save(output_path)


if __name__ == "__main__":
    build_exam_docx("exam_question_format_compact.docx")
