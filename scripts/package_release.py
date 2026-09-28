"""Build a portable source archive; deliberately exclude all runtime data and credentials."""
from pathlib import Path
import zipfile
from check_release import ROOT, check, source_files

check()
output = ROOT / 'dist' / 'openvid-source.zip'
output.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in source_files():
        archive.write(path, 'openvid/' + path.relative_to(ROOT).as_posix())
print(output)
