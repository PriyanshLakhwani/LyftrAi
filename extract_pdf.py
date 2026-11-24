import sys
from pathlib import Path
from PyPDF2 import PdfReader
pdf_path = Path('Lyftr_AI_Full_Stack_Assignment.pdf')
if not pdf_path.is_file():
    print('PDF not found')
    sys.exit(1)
reader = PdfReader(str(pdf_path))
text = ''
for page in reader.pages:
    txt = page.extract_text()
    if txt:
        text += txt + '\n'
print(text)
