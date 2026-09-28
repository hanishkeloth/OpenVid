"""Build a captioned installation-to-export guide; no API calls or simulated jobs."""
from pathlib import Path
import html
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/publishing/walkthrough'
ASSETS = OUT / 'assets'
ASSETS.mkdir(parents=True, exist_ok=True)
for name in ['editor-chart.jpg', 'provider-connections.jpg', 'six-examples.jpg']:
    shutil.copy2(ROOT / 'docs/publishing/assets' / name, ASSETS / name)
shutil.copy2(ROOT / 'brag-output/composition/assets/music.m4a', ASSETS / 'music.m4a')

# Plain instructional cards with product illustrations; no fictional terminal output.
scenes = [
    (8, 'START HERE', 'Your first OpenVid video', 'Install → edit → check narration → export',
     '<div class="hero">A local video presentation workflow.</div><p>Use the six included examples. No AI key is needed to edit and render existing media.</p><div class="pill">Captioned guide · pause to copy commands</div>'),
    (12, '01 / REQUIREMENTS', 'Check your tools', 'macOS / Linux shell commands',
     '<div class="columns"><div><h2>Install first</h2><p>Python 3.13+<br>Node.js 22+<br>Git and FFmpeg / ffprobe</p></div><pre>python3 --version\nnode --version\ngit --version\nffmpeg -version</pre></div><p class="note">PowerPoint import also needs LibreOffice. Follow the repository setup notes for your OS.</p>'),
    (14, '02 / INSTALL', 'Clone and install OpenVid', 'Run these commands in your terminal',
     '<pre>git clone https://github.com/hanishkeloth/OpenVid.git\ncd OpenVid\npython3 -m venv .venv\n.venv/bin/pip install -r requirements.txt\nnpm ci</pre><p class="note">This creates a local Python environment and installs the pinned project dependencies.</p>'),
    (12, '03 / START', 'Install the renderer. Start the app.', 'Keep the terminal running while you work',
     '<pre>npx hyperframes browser ensure\nnpm run dev</pre><div class="url">http://127.0.0.1:7795/vids</div><p>Open this address in your browser. Keep the same browser profile to retain your private workspace.</p>'),
    (12, '04 / CHOOSE AN EXAMPLE', 'Start with a complete project', 'Open the press-announcement project from the library',
     '<img class="shot" src="assets/six-examples.jpg" alt="The six included example projects"><div class="callout">File → Make a copy<br><span>Rename the copy before editing. All example businesses and metrics are fictional.</span></div>'),
    (12, '05 / EDIT', 'Make one small change', 'Select a scene, then select a text layer',
     '<img class="shot" src="assets/editor-chart.jpg" alt="OpenVid scene editor illustration"><div class="callout">Open Format options<br><span>Try a headline colour or font size. Keep the script unchanged for this first export.</span></div>'),
    (14, '06 / TIMING', 'Let every sentence finish', 'Scene → Duration and transition · View → Layers and timing',
     '<div class="formula">Scene duration ≥ voice start + voice duration</div><div class="timeline"><div class="voice">Narration</div><div class="rest">Breathing room</div></div><p>Preview every scene boundary. Keep music quieter than speech and add an end fade.</p><p class="note">Changing a headline or metric does not rewrite the existing narration.</p>'),
    (14, '07 / OPTIONAL VOICEOVER', 'Replace narration when needed', 'Record your own audio, upload a clip, or connect a speech provider',
     '<img class="shot" src="assets/provider-connections.jpg" alt="Provider defaults illustration"><div class="callout">Connections → speech default → Voiceover<br><span>Generate and insert the clip. Remove or mute the old voice. Recheck scene duration.</span></div>'),
    (12, '08 / EXPORT', 'Render an MP4 locally', 'Wait until the editor says All changes saved',
     '<div class="steps"><div>Download<span>Choose MP4</span></div><b>→</b><div>720p · 30 fps<span>A useful first render</span></div><b>→</b><div>Render video<span>Follow the job in Activity</span></div></div><p>Open the completed result and download the file. Watch and listen through the last scene.</p><p class="note">Keep OpenVid running during the render. Local export is separate from optional paid AI generation.</p>'),
    (12, '09 / CHECK', 'Verify the exported file', 'Playback is the final quality check',
     '<pre>ffprobe -v error -show_entries \\\n  stream=codec_type,width,height,duration \\\n  -of json your-video.mp4\n\nffmpeg -v error -i your-video.mp4 -f null -</pre><p class="note">These commands inspect streams and decode the file. Also check readability, voice timing and music volume.</p>'),
    (10, 'KEEP BUILDING', 'Your scenes stay editable', 'Source, examples and the full written tutorial',
     '<div class="url">github.com/hanishkeloth/OpenVid</div><p>Code: AGPL-3.0-only. Sample media has separate notices.<br>Optional AI usage is billed by your connected providers.</p><p class="note">Early release: no Google Drive integration or live cross-workspace collaboration. Project JSON does not bundle media files.</p><div class="pill">Guide uses source-derived UI illustrations, not a live screen recording.</div>'),
]
total = sum(s[0] for s in scenes)
parts = []
animations = []
chapters = []
start = 0
for i, (duration, label, title, subtitle, content) in enumerate(scenes):
    chapters.append(f'{start//60:02}:{start%60:02} {title}')
    parts.append(f'<section class="clip" id="s{i}" data-start="{start}" data-duration="{duration}" data-track-index="{i+1}"><div class="label">{label}</div><h1>{html.escape(title)}</h1><div class="subtitle">{html.escape(subtitle)}</div><div class="body">{content}</div><div class="count">{i+1:02} / {len(scenes):02}</div></section>')
    animations.append(f"document.querySelector('#s{i} .body').animate([{{opacity:0,transform:'translateY(18px)'}},{{opacity:1,transform:'translateY(0)'}}],{{duration:450,delay:{start*1000+100},fill:'both',iterations:1}}).pause();")
    start += duration

page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>OpenVid — installation to export</title><style>
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;font-family:system-ui,sans-serif;background:#f8f9fd;color:#172139}#root{position:relative;width:100%;height:100%;overflow:hidden}.brand{position:absolute;top:44px;left:80px;font-size:30px;font-weight:650}.brand b{display:inline-block;background:#6553e8;color:white;padding:7px 12px;border-radius:11px;margin-right:13px}.footer{position:absolute;bottom:34px;left:80px;font-size:19px;color:#485772}.progress{position:absolute;bottom:0;left:0;height:8px;width:100%;background:#6553e8;transform-origin:left}.clip{position:absolute;inset:0}.label{position:absolute;top:135px;left:80px;color:#5948c9;letter-spacing:3px;font-size:23px;font-weight:650}h1{position:absolute;top:178px;left:80px;margin:0;font-size:70px;letter-spacing:-2px;font-weight:630}.subtitle{position:absolute;top:286px;left:80px;font-size:29px;color:#485772}.body{position:absolute;left:80px;right:80px;top:365px;height:600px}.hero{font-size:76px;max-width:1100px;line-height:1.13;margin:42px 0}p{font-size:33px;line-height:1.5;max-width:1560px;margin:30px 0}.note{font-size:26px;color:#485772}.pill{display:inline-block;font-size:25px;background:#e8e4ff;border-radius:24px;padding:15px 24px;color:#3e309a;margin-top:28px}pre{white-space:pre-wrap;font:29px/1.6 ui-monospace,monospace;background:#172139;color:#f6f7ff;padding:32px 38px;border-radius:20px;margin:0}.columns{display:grid;grid-template-columns:1fr 1fr;gap:60px}h2{font-size:40px;margin:20px 0}.url{font-size:48px;padding:30px 0;color:#4936bb;letter-spacing:-1px}.shot{position:absolute;left:0;top:0;width:1040px;height:585px;object-fit:contain;background:white;border:1px solid #d4daea;border-radius:16px}.callout{position:absolute;left:1110px;top:100px;right:0;font-size:37px;line-height:1.35;font-weight:600}.callout span{display:block;margin-top:30px;font-size:29px;font-weight:400;color:#485772}.formula{font-size:43px;background:#e8e4ff;color:#3e309a;border-radius:18px;padding:28px 35px}.timeline{display:flex;margin-top:35px;gap:10px;height:93px;font-size:27px;align-items:stretch}.voice{width:70%;background:#b5aae9;border-radius:12px;padding:26px}.rest{flex:1;background:#dce9e1;border-radius:12px;padding:26px}.steps{display:flex;align-items:center;gap:28px;margin:60px 0}.steps div{flex:1;padding:34px;background:white;border:2px solid #d4daea;border-radius:20px;font-size:37px}.steps span{display:block;color:#485772;font-size:25px;margin-top:20px}.steps b{font-size:38px;color:#6553e8}.count{position:absolute;bottom:34px;right:80px;font-size:24px;color:#485772}
</style></head><body><div id="root" data-composition-id="openvid-walkthrough" data-no-timeline data-width="1920" data-height="1080" data-duration="__D__"><div class="brand"><b>▶</b>OpenVid</div>__SCENES__<div class="footer">LOCAL WORKFLOW GUIDE · v0.1.0</div><div class="progress" id="progress"></div></div><script>__ANIM__document.querySelector('#progress').animate([{transform:'scaleX(0)'},{transform:'scaleX(1)'}],{duration:__MS__,fill:'both',iterations:1}).pause();</script></body></html>'''
(OUT / 'index.html').write_text(page.replace('__D__', str(total)).replace('__SCENES__', ''.join(parts)).replace('__ANIM__', ''.join(animations)).replace('__MS__', str(total*1000)))
(OUT / 'hyperframes.json').write_text(json.dumps({'name':'openvid-walkthrough'}, indent=2)+'\n')
(ROOT / 'docs/publishing/walkthrough-chapters.txt').write_text('\n'.join(chapters)+'\n')
print(f'Built {total}-second guide with {len(scenes)} chapters.')
