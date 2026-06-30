"""Examine the reference landscape-format.docx and portrait-format.docx"""
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn

for fname in ["landscape-format.docx", "portrait-format.docx"]:
    doc = Document(fname)
    print(f"=== {fname} ===")
    
    for i, sec in enumerate(doc.sections):
        orient = "LANDSCAPE" if sec.orientation == WD_ORIENT.LANDSCAPE else "PORTRAIT"
        print(f"  Section {i}:")
        print(f"    Orientation: {orient}")
        print(f"    Page width: {sec.page_width.cm:.2f} cm")
        print(f"    Page height: {sec.page_height.cm:.2f} cm")
        print(f"    Top margin: {sec.top_margin.cm:.2f} cm")
        print(f"    Bottom margin: {sec.bottom_margin.cm:.2f} cm")
        print(f"    Left margin: {sec.left_margin.cm:.2f} cm")
        print(f"    Right margin: {sec.right_margin.cm:.2f} cm")
        
        cols = sec._sectPr.find(qn("w:cols"))
        if cols is not None:
            num = cols.get(qn("w:num"))
            space = cols.get(qn("w:space"))
            sep = cols.get(qn("w:sep"))
            print(f"    Columns: num={num}, space={space}, sep={sep}")
    
    # Examine styles
    print(f"  Styles:")
    for style in doc.styles:
        if style.type == 1:  # paragraph style
            name = style.name
            if name in ["Normal", "ExamTitle", "ExamMeta", "ExamSectionHeader", "ExamQuestion", "ExamOption", "ExamSection"]:
                font_name = style.font.name
                font_size = style.font.size
                bold = style.font.bold
                indent = style.paragraph_format.left_indent
                space_before = style.paragraph_format.space_before
                space_after = style.paragraph_format.space_after
                line_spacing = style.paragraph_format.line_spacing
                
                size_pt = f"{font_size.pt:.1f}pt" if font_size else "None"
                indent_str = f"{indent.pt:.2f}pt" if indent else "None"
                before_str = f"{space_before.pt:.1f}pt" if space_before else "None"
                after_str = f"{space_after.pt:.1f}pt" if space_after else "None"
                line_str = f"{line_spacing.pt:.1f}pt" if line_spacing else "None"
                
                print(f"    {name}: font={font_name}, size={size_pt}, bold={bold}, indent={indent_str}, before={before_str}, after={after_str}, line={line_str}")
    
    # Examine first few paragraphs
    print(f"  First 10 paragraphs:")
    for j, para in enumerate(doc.paragraphs[:10]):
        style_name = para.style.name
        text = para.text[:80]
        align = para.alignment
        tabs = []
        for stop in para.paragraph_format.tab_stops:
            tabs.append(f"pos={stop.position.pt:.1f}pt, align={stop.alignment}")
        tab_str = ", ".join(tabs) if tabs else "none"
        print(f"    [{j}] style={style_name}, align={align}, tabs=[{tab_str}]")
        print(f"         text: {text}")
    print()
