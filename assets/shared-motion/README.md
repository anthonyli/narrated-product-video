# Deterministic shared motion

Copy this directory to a task workspace. Requires Python 3.10+, Pillow, a local CJK font and FFmpeg with libx264. No installation, downloads, model calls or network access are performed. `VIDEO_FONT_REGULAR` / `VIDEO_FONT_BOLD` may name licensed local font files; the reference adapter also discovers common macOS/Linux CJK fonts.

```sh
python render.py examples/impeccable-v3.json outputs/preview.png --preview-at 6
python render.py examples/impeccable-v3.json outputs/transition.mp4 --start 5 --end 8
python render.py examples/impeccable-v3.json outputs/full.mp4 --ffmpeg /path/to/ffmpeg
python render.py examples/flow-comparison.json outputs/flow.mp4
```

`--fps 30` lowers temporal sampling without changing event timings. Default examples use 1920×1080 / 60 fps. Output paths must be new. `--validate-only` checks the same timeline, output, clip and optional audio constraints without encoding, but **still imports and executes the selected trusted local Python adapter**. Review adapter source before running it.

`--audio work/narration.wav` accepts a complete continuous PCM WAV matching the full timeline within one frame. It is optional for silent visual samples. No speed change, silence padding or implicit fit occurs. Audio is cropped only when explicitly rendering `--start` / `--end`; MP4 audio uses AAC/48kHz. Build the timeline around real semantic paragraph timings before muxing. The renderer does not create or burn narration subtitles.

## Adapter interface

The JSON `adapter` is a relative local Python path. Its `create_scenes(config, config_dir)` returns `core.Scene` objects, each with `id`, source `duration`, `frame(source_time)` and optional `holds` / `rests`. A frame is a Pillow image matching `canvas`; time is in seconds and scene ends are exclusive. Rendering seeks exact frame timestamps and never relies on realtime playback.

The `editorial_ui.py` adapter preserves the approved v3 geometry and movement. All episode-specific text, documents, rule count and attribution live in `examples/impeccable-v3.json`. The example retains its original 52-second timings and longer intentional wipes. Its four command rows, two documents and three inspection regions are layout constraints of this adapter, not universal storytelling rules. Use another adapter or modify the task copy for a different structure. `examples/flow_comparison.py` demonstrates a distinct continuous route comparison through the same core.

The Impeccable example is dated 2026-10-30 and depicts conceptual UI, not an execution result. Recheck facts before reusing it in a new publication.

## Separate resting time from motion

In each reference `scenes` item, source time always refers to the unmodified v3 scene, independent of preceding timing edits:

```json
{
  "id": "context", "source": "context",
  "rests": [{"start": 4.5, "end": 6.0, "duration": 0.7,
             "reason": "Shorter reading interval; semantic narration is complete"}],
  "holds": [{"at": 6.1, "duration": 0.5,
             "reason": "Finish the corresponding spoken clause"}]
}
```

`holds` insert a frozen frame at a stable source point. `rests` replace a **manually verified idle interval** with a chosen duration; zero removes the interval. Source motion outside these ranges keeps its original speed and length. Rest ranges must not overlap, contain an inserted hold, cut an entrance/reflow/focus move or interrupt a transition. A renderer cannot infer which motion carries meaning: inspect the selected interval and every new junction. Ambient motion inside a shortened rest is retimed, so check for visible discontinuity, especially when duration is zero.

Useful reference reading windows, to verify against narration before use: UI after reflow settles and before the wipe; commands after the final selection; context after both documents migrate and before the blue wipe; detector after the bridge appears and before the circle wipe; local-boundary after the three statements appear; outro after the source URL reveals. Do not treat the entire scene as a rest.

## Verification

```sh
python -m unittest discover -s tests -v
```

Tests cover frame timing, independent hold/rest edits, scene boundaries, audio completeness and exclusive output creation. They do not establish visual quality. Preview key states; render and play every changed junction, compare normal-speed motion with the reference, decode the complete MP4, and check media dimensions/timing. When narration is present, separately review pronunciations, completeness and semantic synchronization.
