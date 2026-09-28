# OpenVid product video

Created with the `brag` workflow and HyperFrames 0.8.77. The 24-second, 1920×1080, 30fps video shows the editor, animated chart, Connections task defaults and all six examples. It is a source-derived product demonstration with staged cursor actions, not a recording of live provider calls.

- Published video: [openvid-product.mp4](../docs/assets/openvid-product.mp4)
- Poster: [openvid-product.jpg](../docs/assets/openvid-product.jpg), taken at 9 seconds and also baked into frame zero.
- [Storyboard](brag-plan.md), [composition brief](composition-brief.md), and [share caption](share-copy.txt).
- Editable HyperFrames source: [composition/index.html](composition/index.html).

From the repository root, after installing project dependencies:

```sh
python3 brag-output/build_composition.py
npx hyperframes check brag-output/composition
npx hyperframes preview brag-output/composition --port 3017
npx hyperframes render brag-output/composition --quality delivery --fps 30 --workers 2 --output brag-output/brag.mp4
```

The generator uses the public Aurelia scene document and the included pre-extracted audio envelope. The composition has no runtime API calls or credentials. Its animation uses finite native Web Animations API keyframes. HyperFrames may resolve system fonts during compilation.

## Media credits

Composition code and original layouts use the repository's AGPL-3.0-only licence. Photographs and sample poster images retain the Pexels terms and attribution in [the business asset notice](../examples/business/ASSETS.md) and [stock credits](../examples/business/stock-credits.json). Companies, stories and chart metrics are fictional examples.

`composition/assets/music.m4a` is a 24-second excerpt of the existing Aurelia instrumental, generated with Sonilo 1.1 through fal.ai for this project. Its output terms are described in the business asset notice; it is not third-party stock music from the brag skill. The final mix uses a 0.32 music gain and a three-second fade to silence.

`composition/assets/click.ogg` (UI Audio, click2) and `reveal.ogg` (Impact Sounds, impactSoft_medium_001) are Kenney CC0 sounds, sourced from the brag skill's bundled Kenney library. Original asset collections: [UI Audio](https://kenney.nl/assets/ui-audio) and [Impact Sounds](https://kenney.nl/assets/impact-sounds). CC0 assets retain their public-domain dedication.

## Verification

HyperFrames check passed with zero errors in lint, runtime, layout and contrast. Five non-blocking static warnings concern a repeated preview image and grouped scene markup. The encoded video decodes completely: H.264, AAC, 720 video frames, exactly 24 seconds. The editor/chart, provider-selection and final frames were visually reviewed, and the final music fade was measured down to silence. No narration is included.
