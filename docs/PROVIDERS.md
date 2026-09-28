# Provider integration notes

Connections stores a provider key, model IDs, optional custom endpoint URL and per-task input overrides. Defaults are selected separately for planning, images, video, speech, music and transcription. Saving a key does not verify model entitlement; the Test button only checks a read-only account or catalog endpoint.

- **OpenAI:** `/v1/chat/completions`, `/images/generations`, `/images/edits`, `/audio/speech`, `/audio/transcriptions`. Speech model default `gpt-4o-mini-tts`; choose an OpenAI voice such as coral. Long narration must be split into clips of at most 4,096 characters. `whisper-1` transcription requests word timing. Custom models may need different settings.
- **Anthropic:** `/v1/messages`; JSON edit proposals are validated before being offered in the editor. Focused changes use bounded JSON Patch operations so a long document need not be regenerated.
- **Gemini:** `/v1beta/interactions` with `x-goog-api-key`. Model ID is editable. This adapter is included but has not yet been live-verified in OpenVid.
- **ElevenLabs:** direct v3 speech with timing, Scribe transcription, shared voice library, voice design and instant cloning. Names/IDs must be available in your account. Language options come from the live v3 model catalog. Cloning requires permission and any provider-required verification; it is not a bypass for verification.
- **fal:** queue submission and stored request IDs via fal-client. Defaults use Nano Banana 2 Lite, Gemini Omni Flash 1.1, ElevenLabs v3, Sonilo 1.1, Scribe v2 and OmniHuman 1.5. Each endpoint can be changed. Reference-image video uses the matching image-to-video endpoint when the text endpoint follows that naming convention. For image references, set an `/edit` endpoint. Inputs vary by model, so configure advanced JSON fields from the model’s published schema. All media comes back into the local workspace.
- **Replicate:** an explicit `owner/model`, predictions endpoint, persistent prediction ID and polling. Configure model-specific inputs under the task name. The generic adapter uses `prompt`, and for reference images `image`; models expecting other field names require adapter work. This is not a claim that every Replicate model works unchanged.
- **OpenAI-compatible:** expects the same REST route and response structure as the OpenAI adapter. Compatibility must be checked per endpoint. No silent fallback to another paid provider occurs when a selected connection fails.
- **Stock:** server-side Pexels/Pixabay keys; Wikimedia Commons public search. Imported assets retain provider, creator, source and licence attribution.

Examples of advanced inputs:

```json
{"video":{"resolution":"720p"},"avatar":{"resolution":"720p"}}
```

Changing the task’s prompt/duration in advanced inputs overrides the editor values. Avoid setting them unless that is intentional. Prices are provider-specific; OpenVid does not maintain a universal live price catalog. Review costs and quotas in your provider dashboard.

References: [OpenAI image API](https://developers.openai.com/api/docs/guides/image-generation), [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create), [Gemini text generation](https://ai.google.dev/gemini-api/docs/text-generation), [ElevenLabs speech timing](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps), [fal Nano Banana Lite schema](https://fal.ai/models/google/nano-banana-2-lite/api), [Replicate HTTP API](https://replicate.com/docs/reference/http).
