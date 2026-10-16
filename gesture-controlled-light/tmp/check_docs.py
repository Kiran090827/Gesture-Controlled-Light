from pathlib import Path
from zipfile import ZipFile
for p in [Path('Gesture-Controlled-Light-POC.docx'),Path('Gesture-Controlled-Light-Project-Access-Guide.docx')]:
 d=Document = __import__('docx').Document(p)
 headings=[x.text for x in d.paragraphs if x.style.name.startswith('Heading')]
 tables=len(d.tables)
 print(f'{p.name}: {p.stat().st_size} bytes; paragraphs={len(d.paragraphs)}; tables={tables}; headings={len(headings)}; title={d.core_properties.title}')
 print('  first headings:', ' | '.join(headings[:5]))
z=Path(r'C:\Users\Kiran Rao\OneDrive\Documents\Gesture controlled light\gesture-controlled-light.zip')
with ZipFile(z) as f:
 print(f'ZIP entries={len(f.namelist())}; has docs={[n for n in f.namelist() if n.lower().endswith(".docx")]}')
