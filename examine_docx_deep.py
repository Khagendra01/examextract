"""Deep dive into the reference docx files - extract raw XML of first few paragraphs"""
from docx import Document
from lxml import etree

for fname in ["landscape-format.docx", "portrait-format.docx"]:
    doc = Document(fname)
    print(f"=== {fname} ===")
    
    # Get raw XML of first 5 paragraphs
    for i, para in enumerate(doc.paragraphs[:8]):
        print(f"\n--- Paragraph {i} ---")
        print(f"Text: {repr(para.text[:100])}")
        print(f"Style: {para.style.name}")
        
        # Get the full XML of the paragraph element
        xml = etree.tostring(para._element, pretty_print=True).decode()
        # Only print the first 600 chars to keep it readable
        print(f"XML (trimmed):")
        print(xml[:600])
        print()
    
    # Also check the section XML for columns
    sec = doc.sections[0]
    sect_xml = etree.tostring(sec._sectPr, pretty_print=True).decode()
    print(f"\n--- Section XML ---")
    print(sect_xml)
    print("\n" + "="*80)
