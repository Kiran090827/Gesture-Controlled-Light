from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
root=Path.cwd()
archive=root.parent/'gesture-controlled-light.zip'
files=['Gesture-Controlled-Light-POC.docx','Gesture-Controlled-Light-Project-Access-Guide.docx','Gesture-Controlled-Light-Documentation.pdf']
with ZipFile(archive,'a',compression=ZIP_DEFLATED) as z:
 existing=set(z.namelist())
 for name in files:
  if name not in existing:
   z.write(root/name,arcname=name)
with ZipFile(archive) as z:
 print('Archive:',archive.resolve())
 print('Added documentation:', [n for n in z.namelist() if n in files])
 print('Total entries:',len(z.namelist()))
print('Size:',archive.stat().st_size)
