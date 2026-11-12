"""Regenerate templates/reference.docx: pandoc's default styles, restyled plain for ATS.

Run: pandoc -o templates/reference.docx --print-default-data-file reference.docx
     uv run python tools/make_reference_docx.py
"""

import re
import shutil
import tempfile
import zipfile
from pathlib import Path

DOCX = Path(__file__).parents[1] / "templates" / "reference.docx"
FONT = '<w:rFonts w:ascii="Calibri" w:eastAsia="Calibri" w:hAnsi="Calibri" w:cs="Calibri" />'


def restyle(xml: str) -> str:
    xml = re.sub(r"<w:rFonts [^>]*Theme[^>]*/>", FONT, xml)
    xml = re.sub(r'<w:color w:val="[0-9A-F]+"[^>]*/>', '<w:color w:val="000000" />', xml)
    xml = xml.replace('<w:sz w:val="24" />\n        <w:szCs w:val="24" />',
                      '<w:sz w:val="21" />\n        <w:szCs w:val="21" />', 1)
    sizes = {"Heading1": "36", "Heading2": "22", "Heading3": "21"}
    for style, size in sizes.items():
        start = xml.find(f'w:styleId="{style}"')
        end = xml.find("</w:style>", start)
        block = re.sub(r'w:val="\d+" />(\s*)<w:szCs w:val="\d+"', f'w:val="{size}" />\1<w:szCs w:val="{size}"', xml[start:end])
        block = block.replace(FONT, FONT + "\n      <w:b />", 1)  # schema order: rFonts before b
        xml = xml[:start] + block + xml[end:]
    start = xml.find('w:styleId="BodyText"')
    end = xml.find("</w:style>", start)
    xml = xml[:start] + xml[start:end].replace('w:before="180" w:after="180"', 'w:before="0" w:after="80"') + xml[end:]
    return xml


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "reference.docx"
        with zipfile.ZipFile(DOCX) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
            for item in src.infolist():
                data = src.read(item)
                if item.filename == "word/styles.xml":
                    data = restyle(data.decode("utf-8")).encode("utf-8")
                dst.writestr(item, data)
        shutil.copy(out, DOCX)


if __name__ == "__main__":
    main()
