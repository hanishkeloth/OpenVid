# HyperFrames composition brief: OpenVid

Create the 24-second landscape product video defined in brag-plan.md. Output composition/index.html, brag.mp4, brag.jpg, and share-copy.txt.

Source: README.md; web/vids.html, vids.css, vids.js, connections.js; examples/business/press.json and the six existing docs/assets preview images. Show the source-derived editor layout, timeline and artwork. Enlarge controls for video legibility without changing their meaning. Use the actual copy “Connections”, “Choose a provider for each task”, and “Save defaults”.

Palette: #fafbff paper, #172139 ink, #6553e8 accent; editor surfaces #f8fafd and #eaf0fa. Use portable system sans-serif. Keep UI text at least 22px where practical, headlines 78–96px. Existing sample artwork keeps its own colours and fictional-data notice.

Runtime: native Web Animations API, synchronous finite paused animations with fill both. Timed clips are framework-owned. No GSAP dependency, network assets, timers, or interaction-dependent rendering. Source sample layers supply the canvas artwork. Cursor motion is an explicit staged demonstration of real controls.

Audio: Aurelia's Sonilo 1.1 instrumental, copied and trimmed locally to 24 seconds; volume 0.32, fade-in 0.4 seconds, fade-out 3 seconds. Three quiet Kenney CC0 interface/reveal effects. No narration. Analyze beats after the local music element exists. Pre-extract audio bands and use finite per-frame WAAPI keyframes to vary the background accent's opacity subtly. Keep text steady.

Validate with HyperFrames check including contrast, layout and runtime. Preview in Brave, then render the user-requested final MP4 at 1080p, 30fps, delivery quality. Verify decoded frames, audio presence, duration and final hold. Choose the settled editor/chart poster and replace only frame zero. Publish the MP4 and poster in docs/assets and link from the README.
