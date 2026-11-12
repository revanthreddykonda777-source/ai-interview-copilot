import os
import zipfile
import xml.etree.ElementTree as ET
import pdfplumber

MAX_DOCX_XML_BYTES = 5 * 1024 * 1024


def _extract_pdf_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def _extract_docx_text(docx_path):
    with zipfile.ZipFile(docx_path, "r") as zf:
        if "word/document.xml" not in zf.namelist():
            return ""
        info = zf.getinfo("word/document.xml")
        if info.file_size > MAX_DOCX_XML_BYTES:
            raise ValueError("DOCX document.xml exceeds size safety limit.")
        xml_bytes = zf.read("word/document.xml")

    root = ET.fromstring(xml_bytes)
    paragraphs = []
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for p in root.findall(".//w:p", ns):
        runs = [t.text for t in p.findall(".//w:t", ns) if t.text]
        if runs:
            paragraphs.append("".join(runs))
    return "\n".join(paragraphs)


def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".docx":
            return _extract_docx_text(file_path)
        return _extract_pdf_text(file_path)
    except Exception as e:
        print(f"Error reading resume ({ext}): {e}")
        return None
