# Publication assets

- `dev-tutorial.md`: source of the published practical tutorial.
- `listing-copy.md`: directory descriptions, Product Hunt maker comment and YouTube metadata.
- `assets/`: product illustrations extracted from the 24-second tour, plus the OpenVid icon.
- `walkthrough/`: editable HyperFrames source for the 2:12 captioned installation-to-export guide.
- `walkthrough-chapters.txt`: chapter timestamps for YouTube.

The guide presents setup commands, choosing and copying an example, editing a scene, aligning narration, optional speech generation, exporting, and checking the result. It uses instructional cards and source-derived product illustrations. It is not a live screen recording and does not depict actual provider requests. There is no spoken narration in the guide; the on-screen instructions carry the tutorial.

Rebuild from the repository root:

```sh
python3 docs/publishing/build_walkthrough.py
npx hyperframes check docs/publishing/walkthrough
npx hyperframes render docs/publishing/walkthrough --quality delivery --fps 30 --workers 2 --output /tmp/openvid-walkthrough-silent.mp4
python3 docs/publishing/finish_walkthrough.py /tmp/openvid-walkthrough-silent.mp4
```

The finished guide reuses the existing Aurelia instrumental at low volume with overlapping loop boundaries and a three-second end fade. Music, stock photographs and fictional sample projects retain the notices in [the business media credits](../../examples/business/ASSETS.md). The code and original layouts use AGPL-3.0-only.

Publication state is tracked in [LAUNCH.md](../LAUNCH.md). Drafts and review-queue entries are not live launches.

Verification: the guide passed HyperFrames runtime, layout and motion checks, with 49/49 contrast checks passing. Eleven non-blocking lint warnings concern grouping timeline sections. All eleven chapter frames were visually reviewed. The finished file is H.264/AAC, 1920×1080, exactly 132 seconds; full-file FFmpeg decoding completed without errors.
