# v4 — executable editorial design + transitions (2026-10-31 UTC+08)

## Added
- `assets/shared-motion/transitions.py`: deterministic ripple (refractive wavefront), radial reveal and perspective-like card flip. Exact endpoint frames, semantic origin, bounded options, no random style sampling.
- `assets/editorial-motion/editorial_samples.py`: six original parameterized 1080p layouts: report_hero, ledger, process_note, notebook, index_detail, timeline. Config-driven silent MP4 renderer. Topic/palette fields are explicit; arbitrary scene JSON and automatic text fit are not claimed.
- Editorial design workflow: argument→information form→authored keyframes→visual inspection→semantic transition→actual timed sample→final review. Not “more movement means better”.
- Visual-plan checker and schema2/editorial-v4 acceptance: keyframe artifact hashes, five explicit art-direction criteria, content-bound transition plan and rendered before/middle/after reviews. Legacy schema1 cannot satisfy `--require-profile editorial-v4`.
- Additive transition/property and acceptance negative tests. Existing core renderer/audio interfaces preserved.

## Compatibility / limits
- No changes to authorized voice pipeline or shared-motion/core.py. `run_cpu_voice.sh` restored executable bit after ZIP recovery.
- Reference footage/screenshots, private voices/models, outputs, user configuration and secrets are not distributed.
- Evidence checkers are not beauty classifiers and do not prove reviewer honesty. Actual frame inspection/playback remains mandatory. No perpetual cache claim.
- Layouts use installed Noto CJK + DejaVu fonts, Pillow, NumPy, FFmpeg. They do not install or run promoted projects. No paid service/key required.
- Ripple/flip are new Python/PIL APIs, not aliases for unsupported legacy JSON fields. Flip is not fluid page-curl simulation.
