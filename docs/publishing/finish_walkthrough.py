"""Mix the existing example instrumental into a rendered silent guide."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
video = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/openvid-walkthrough-silent.mp4')
music = root / 'examples/business/media/samples/press/3591289057f3.m4a'
output = root / 'docs/assets/openvid-walkthrough.mp4'
subprocess.run([
    'ffmpeg', '-y', '-v', 'error', '-i', str(video), '-i', str(music),
    '-filter_complex',
    '[1:a]asplit=4[a][b][c][d];'
    '[a][b]acrossfade=d=2:c1=tri:c2=tri[ab];'
    '[ab][c]acrossfade=d=2:c1=tri:c2=tri[abc];'
    '[abc][d]acrossfade=d=2:c1=tri:c2=tri,'
    'atrim=duration=132,volume=0.22,afade=t=in:d=1,afade=t=out:st=129:d=3[music]',
    '-map', '0:v:0', '-map', '[music]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
    '-t', '132', '-movflags', '+faststart', str(output),
], check=True)
print('Created docs/assets/openvid-walkthrough.mp4')
