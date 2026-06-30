# pip install python-docx
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


CONTENT = [('Third Terminal Examination 2082', 'ExamTitle', 1, []),
 ('Sub: Math\tFM: 50', 'ExamMeta', None, [(6941, 'RIGHT')]),
 ('Class: 6\tTime: 1.30 hrs\tPM: 20', 'ExamMeta', None, [(3341, 'CENTER'), (6941, 'RIGHT')]),
 ('******************************************************', 'Normal', None, []),
 ('Attempt the questions.', 'ExamSectionHeader', None, []),
 ('1) write the following in set notation. [2]', 'ExamQuestion', None, []),
 ('a) 2 belongs to the set of natural number N', 'ExamQuestion', None, []),
 ('b) 1/5 does not belong to the set N', 'ExamQuestion', None, []),
 ('2) a) The smallest number which is exactly divisible by the given numbers is called its __________. [1]', 'ExamQuestion', None, []),
 ('b) A man has Rs 1500, He bought 5 copies costing Rs 80 and 8 pen costing Rs 75 each.', 'ExamQuestion', None, []),
 ('i) convert the above statement into mathematical expression [1]', 'ExamQuestion', None, []),
 ('ii) simplify the expression and find how much money left with him [1]', 'ExamQuestion', None, []),
 ('9) write the set of prime numbers less than 10 [1]', 'ExamQuestion', None, []),
 ('4) a) Factorise 20 and 30 separately [2]', 'ExamQuestion', None, []),
 ('b) Find the product of common prime factors of 20 and 30 [1]', 'ExamQuestion', None, []),
 ('5) using prime factorisation method, find the l.c.m of 18 and 24 [2]', 'ExamQuestion', None, []),
 ('6) Find the square root of 324 [3]', 'ExamQuestion', None, []),
 ('7) lapa spends 1/2 part of his monthly income on food 1/4 part on fuel and 1/8 part on education on which items does he spend more money? [2]', 'ExamQuestion', None, []),
 ('8) weight of three bags are 2 1/2 kg, 3 1/4 kg and 5 1/8 kg respectively, what is the total weight of three bags [2]', 'ExamQuestion', None, []),
 ('10) Find the value of [2]', 'ExamQuestion', None, []),
 ('a) 2/3 of 48', 'ExamQuestion', None, []),
 ('11) simplify [2]', 'ExamQuestion', None, []),
 ('a) 9 ÷ 1/15', 'ExamQuestion', None, []),
 ('12) A man bought a mobile set for Rs 25000 and sold it for a profit of Rs 3700. find it sp. [2]', 'ExamQuestion', None, []),
 ('13) If the cost of 60 apples is Rs 540, what is the cost of 50 apples [2]', 'ExamQuestion', None, []),
 ('14) my height is 172cm convert my height into', 'ExamQuestion', None, []),
 ('i) inches [2]', 'ExamQuestion', None, []),
 ('ii) feet [2]', 'ExamQuestion', None, [])]


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


def build_exam_docx(output_path: str):
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

    # --- Write the exact content used in the sample file ---
    for text, style_name, alignment_int, tabs in CONTENT:
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
    build_exam_docx("math_exam_extracted.docx")