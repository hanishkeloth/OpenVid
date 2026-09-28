# Create a narrated video presentation locally with OpenVid

A video presentation is easier to revise when the source is still a set of editable scenes. In this tutorial, we'll run OpenVid locally, open a four-scene example with narration and music, make a small edit, and render an MP4 on our own computer.

I'm OpenVid's maintainer. The application is open source under AGPL-3.0-only. The first workflow below needs no AI provider account: the repository includes six complete example projects and their media. Optional AI steps use your own provider accounts and can incur charges.

Source: https://github.com/hanishkeloth/OpenVid

Finished examples: https://hanishkeloth.github.io/OpenVid/#examples

## 1. Install the local app

You'll need Python 3.13 or newer, Node.js 22 or newer, Git, and FFmpeg/ffprobe. HyperFrames also needs its supported Chromium installation. LibreOffice is optional; install it if you want to import PowerPoint files.

The following commands use a macOS/Linux-style shell:

```sh
git clone https://github.com/hanishkeloth/OpenVid.git
cd OpenVid
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
npx hyperframes browser ensure
npm run dev
```

On macOS, `brew install ffmpeg` supplies FFmpeg and ffprobe. Check your prerequisites with `python3 --version`, `node --version`, and `ffmpeg -version` before troubleshooting the application itself.

Open `http://127.0.0.1:7795/vids` in your browser. Keep the terminal running while editing or rendering.

The browser receives a private workspace cookie. Keep using the same browser profile: another profile creates a separate workspace, with separate example copies and provider connections.

## 2. Start with the press-announcement example

Open the press-announcement project from the video library. It contains four editable scenes, narration clips, a shared music track, photographs, and an existing finished export.

Before editing, choose **File → Make a copy**. Rename your copy to something recognizable, such as `My first OpenVid presentation`.

Press **Play** to understand the starting sequence. The scene cards at the bottom let you jump between sections. Select a text layer and use **Format options** to change its appearance. For a first experiment, change a headline's colour or font size while keeping the script unchanged. That lets you verify the editing and rendering path without creating mismatched narration.

The examples use fictional businesses and illustrative metrics. Replace those with your own material before publishing a business presentation.

## 3. Keep scene timing and narration aligned

Open **Scene → Duration and transition** to inspect a scene's timing. **View → Layers and timing** exposes individual layer timing.

A useful check is:

```text
scene duration >= narration start + narration duration
```

Leave a little time after the final sentence so the next scene does not feel rushed. A scene's text, visual layers, and narration should also agree about what is being presented. Changing an on-screen number does not rewrite an existing voice recording.

The included soundtrack is shared across the document. Select its audio track to adjust volume and fades. Lower the music until narration remains clear, and use a fade at the end. Listen across each scene boundary, not just from the opening.

For this first export, keeping the bundled narration is the simplest way to test the full workflow without an API key.

## 4. Optionally record or generate new narration

To use your own recording, use **Record** or upload an audio file through **Uploads**. Recording requires your browser's microphone permission.

For AI narration, open **Connections**, configure a supported speech provider, and select it as the speech default. Then open **Voiceover**, enter the scene's script, and choose a voice supported by that provider. Generate the clip and add the completed result to the intended scene.

Remove or mute the old narration before inserting its replacement. Play the scene again and check its duration; avoid leaving two voices speaking at once. Reuse the same voice across scenes when you want a consistent narrator.

Provider model names, account access, and costs vary. A saved connection is not a guarantee that every model is available. OpenVid's [provider notes](https://github.com/hanishkeloth/OpenVid/blob/main/docs/PROVIDERS.md) describe the supported adapters and their limits.

## 5. Render an MP4 locally

Wait for the editor to show **All changes saved**. Select **Download**, choose **MP4**, **720p**, and **30 fps** for a first render, then select **Render video**.

Follow the job in **Activity**. When it completes, open the result and download the finished video. HyperFrames renders the saved scenes and mixes their media on the machine running OpenVid. Optional AI generation is separate from this local rendering step.

Check the exported file itself, including the last scene. A successful job status doesn't tell you whether a headline is too small or music is too loud.

If you want a technical file check:

```sh
ffprobe -v error \
  -show_entries stream=codec_type,width,height,duration \
  -of json your-video.mp4

ffmpeg -v error -i your-video.mp4 -f null -
```

The first command reports the streams and dimensions. The second decodes the entire file and reports decoding errors; neither replaces watching and listening.

## Troubleshooting and current limits

- **Rendering fails immediately:** check FFmpeg and run `npx hyperframes browser ensure` from the repository directory.
- **Your projects seem to disappear:** confirm you are using the same browser profile and local server data directory.
- **Speech overlaps or cuts off:** inspect the audio layers, their start times, and the scene duration; remove the replaced clip.
- **Fonts differ:** install the fonts used by your document, or choose fonts present on the rendering machine.
- **A generation job is interrupted:** inspect its provider status before submitting another paid request. Don't restart the server during an active render or generation.

OpenVid does not currently include Google Drive integration or live collaboration across workspaces. PDF/PPTX pages import as images. Exporting project JSON does not package its media files, so retain the assets when moving an editable project.

Application code and sample media have different licence terms. The repository includes the media notices and credits; preserve them when redistributing the examples.

If you try this workflow, the most useful feedback is a reproducible issue with your operating system, the step that failed, and any non-sensitive error text. Never include API keys or your private workspace cookie in an issue.

*This tutorial was prepared with AI assistance and checked against OpenVid's source and local export workflow.*
