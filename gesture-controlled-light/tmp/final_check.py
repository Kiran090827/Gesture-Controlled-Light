from pathlib import Path
from zipfile import ZipFile
p=Path(r'C:\Users\Kiran Rao\OneDrive\Documents\Gesture controlled light\gesture-controlled-light.zip')
with ZipFile(p) as z:
 print('ZIP integrity:', z.testzip() or 'OK')
 for n in ['Gesture-Controlled-Light-POC.docx','Gesture-Controlled-Light-Project-Access-Guide.docx','Gesture-Controlled-Light-Documentation.pdf']:
  print(n, z.getinfo(n).file_size)
for n in ['Gesture-Controlled-Light-POC.docx','Gesture-Controlled-Light-Project-Access-Guide.docx']:
 f=Path(n); print('DOCX exists:', f.resolve(), f.stat().st_size)
