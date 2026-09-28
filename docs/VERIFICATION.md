# Verification — 28 September 2026

Verified locally with OpenVid’s own Python environment and Node dependencies:

- Six backend tests: workspace isolation for documents/projects/jobs/media, revision conflicts, encrypted credentials, credential removal, idempotent submissions, provider dispatch, custom endpoint validation, cross-origin writes, and assistant patches preserving untouched layers.
- Five editor/compiler tests: text escaping, media trim/speed/gain/fades, scene boundaries, shared music, subtitle round trips, hidden layers and media-preserving scene splits.
- All six example projects load from bundled local assets without API keys.
- Brave: library, Connections, editable provider fields, sample editor and preview controls inspected.
- A complete 40.7-second press-announcement example rendered through the native Web Animations compiler to 1280×720, 30 fps MP4. FFmpeg decoded the entire output without errors. Representative frames were visually reviewed.
- Actual OpenAI `gpt-4o-mini-tts` speech: completed, 6.048-second clip.
- Actual Standard-tier fal `google/nano-banana-2-lite` image: completed and saved locally with its provider request ID.
- Actual Anthropic focused scene edit: succeeded and preserved all four scenes and layers. The initial full-document response exceeded practical output size; the final implementation uses compact JSON Patch for focused edits.
- Actual direct ElevenLabs v3 speech and Scribe transcription: completed, with timed words returned.
- Temporary verification connections were removed. No keys are distributed with the code or examples.

Not claimed as verified: every configurable model, Gemini/Replicate/custom-endpoint live generation, every language/voice, paid video editing or avatars, all export formats/resolutions, or a production-scale multi-user workload. Bundled MP4s are 1080p; the new standalone render check was 720p. Docker/hosting files are included; a Docker image build is separate from these local checks.
