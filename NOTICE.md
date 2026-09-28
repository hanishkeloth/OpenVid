# OpenVid notices

OpenVid was extracted from the Palette Vids implementation and reworked into a standalone application in September 2026. Copyright 2026 OpenVid contributors. The application code is distributed under **GNU AGPL version 3 only**; see [LICENSE](LICENSE).

The original Palette workflow was built around [OpenMontage](https://github.com/calesthio/OpenMontage), distributed under AGPL-3.0. OpenVid does not ship the Palette engine, its private configuration, or its customer data. It provides its own provider adapters, workspace storage, and job runner.

Dependency licences remain their own:

- HyperFrames 0.8.77: Apache-2.0, as declared in its package metadata. Its notices remain in the installed package.
- PyMuPDF: AGPL-3.0 or an Artifex commercial licence. This distribution uses the AGPL option.
- FastAPI, Uvicorn, requests, cryptography, fal-client, Node, Python and other dependencies: see their installed package metadata and licence files.
- FFmpeg, LibreOffice and system fonts: their respective distribution licences, included with those system packages.

OpenVid’s scene compiler uses the browser Web Animations API. GSAP is not a direct application dependency.

The application licence does **not** relicense third-party media or grant trademark, likeness, voice, or provider-service rights. See [examples/business/ASSETS.md](examples/business/ASSETS.md). OpenVid is independent of Google Vids, Google Flow, OpenAI, Anthropic, ElevenLabs, fal.ai, and the other connected services.
