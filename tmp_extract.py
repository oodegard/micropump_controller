from pathlib import Path
import PyPDF2

pdf_path = Path(r'hardware/datasheets/Bartels Operating Manual for controller mp-x.pdf')
reader = PyPDF2.PdfReader(str(pdf_path))
for i, page in enumerate(reader.pages, start=1):
    text = page.extract_text()
    print('PAGE', i, 'len', 0 if text is None else len(text or ''))
