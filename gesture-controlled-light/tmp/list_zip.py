from zipfile import ZipFile
p=r'C:\Users\Kiran Rao\OneDrive\Documents\Gesture controlled light\gesture-controlled-light.zip'
with ZipFile(p) as f:
 for n in f.namelist(): print(n)
