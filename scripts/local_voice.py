#!/usr/bin/env python3
"""Generate a continuous narration with an explicitly authorized local voice."""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import traceback
import wave


@dataclass(frozen=True)
class VoicePlan:
    model: Path
    reference_audio: Path
    text: str = field(repr=False)
    reference_text: str = field(repr=False)
    output: Path
    language: str = "Chinese"
    max_tokens: int = 4096
    log: Path | None = None


def local_path(value, base, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty relative local path")
    if value.startswith(("~", "//", "\\\\")) or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value):
        raise ValueError(f"{label} must be a relative local path, without a URL or ~")
    candidate = Path(value)
    if candidate.is_absolute():
        raise ValueError(f"{label} must be relative to the voice configuration")
    return (base / candidate).resolve()


def require_file(path, label):
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"{label} must be an existing nonempty file")


def read_text(path, label):
    require_file(path, label)
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"{label} must not be blank")
    return value


def wav_info(path):
    """Read every PCM frame; a valid header alone does not prove a complete WAV."""
    require_file(path, "WAV")
    try:
        with wave.open(str(path), "rb") as audio:
            frames = audio.getnframes()
            channels = audio.getnchannels()
            rate = audio.getframerate()
            if frames <= 0 or rate <= 0 or audio.getcomptype() != "NONE":
                raise ValueError("WAV must contain nonempty PCM audio")
            expected = frames * channels * audio.getsampwidth()
            observed = 0
            while block := audio.readframes(65536):
                observed += len(block)
            if observed != expected:
                raise ValueError("WAV sample data is truncated")
            return {"frames": frames, "sample_rate": rate, "channels": channels,
                    "duration_seconds": frames / rate}
    except (wave.Error, EOFError) as error:
        raise ValueError("WAV is not a readable PCM file") from error


def prepare_plan(config_path, text_path, output_path, *, language="Chinese", max_tokens=4096, log_path=None):
    config_path = Path(config_path).resolve()
    require_file(config_path, "voice configuration")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ValueError("voice configuration must be UTF-8 JSON") from error
    if not isinstance(config, dict):
        raise ValueError("voice configuration must be a JSON object")
    if config.get("backend", "local") != "local":
        raise ValueError("Only backend=local is supported; there is no cloud fallback")
    consent = config.get("consent", {})
    if not isinstance(consent, dict) or consent.get("authorized") is not True or \
            consent.get("speaker") not in {"self", "authorized_speaker"} or \
            consent.get("scope") != "local_narration":
        raise ValueError("Record actual consent for self/authorized_speaker local_narration before synthesis")
    preferred = config.get("preferred_voice")
    if not isinstance(preferred, dict):
        raise ValueError("preferred_voice.model must name the local model directory")
    base = config_path.parent
    model = local_path(preferred.get("model"), base, "preferred_voice.model")
    if not model.is_dir():
        raise ValueError("Local model directory is missing; this script never downloads models")
    require_file(model / "config.json", "model config.json")
    if not any(p.is_file() and p.stat().st_size > 0 for p in model.glob("*.safetensors")):
        raise ValueError("Local model directory has no nonempty safetensors weights")
    reference = local_path(config.get("reference_audio"), base, "reference_audio")
    wav_info(reference)
    reference_text_path = local_path(config.get("reference_text_file"), base, "reference_text_file")
    reference_text = read_text(reference_text_path, "reference transcription")
    text = read_text(Path(text_path).resolve(), "narration text")
    output = Path(output_path).absolute()
    if output.suffix.lower() != ".wav":
        raise ValueError("Output must use the .wav extension")
    if output.exists() or output.is_symlink():
        raise FileExistsError("Output already exists; choose a new filename to preserve it")
    if not isinstance(language, str) or not language.strip():
        raise ValueError("language must be nonempty")
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
        raise ValueError("max_tokens must be a positive integer")
    log = Path(log_path).absolute() if log_path else None
    if log and (log.resolve() == output.resolve() or log.exists() or log.is_symlink()):
        raise FileExistsError("Log must use a new path distinct from the output")
    return VoicePlan(model, reference, text, reference_text, output, language, max_tokens, log)


def load_backend():
    # Imported only after offline mode is set; --check-only never imports MLX.
    from mlx_audio.tts.generate import generate_audio
    from mlx_audio.tts.utils import load_model
    return load_model, generate_audio


def synthesize(plan):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    if plan.output.exists() or plan.output.is_symlink():
        raise FileExistsError("Output already exists; choose a new filename to preserve it")
    plan.output.parent.mkdir(parents=True, exist_ok=True)
    if plan.log:
        plan.log.parent.mkdir(parents=True, exist_ok=True)
        # Upstream may print narration even with verbose=False. Logs are opt-in.
        descriptor = os.open(plan.log, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        diagnostics = os.fdopen(descriptor, "w", encoding="utf-8")
    else:
        diagnostics = open(os.devnull, "w", encoding="utf-8")
    with diagnostics, tempfile.TemporaryDirectory(prefix=".local-voice-", dir=plan.output.parent) as temporary:
        generated = Path(temporary) / "narration.wav"
        try:
            with redirect_stdout(diagnostics), redirect_stderr(diagnostics):
                try:
                    load_model, generate_audio = load_backend()
                    model = load_model(str(plan.model))
                    generate_audio(model=model, text=plan.text,
                                   ref_audio=str(plan.reference_audio), ref_text=plan.reference_text,
                                   lang_code=plan.language, max_tokens=plan.max_tokens,
                                   voice=None, stt_model=None, speed=1.0,
                                   file_prefix=str(generated.with_suffix("")), audio_format="wav",
                                   join_audio=True, play=False, stream=False, verbose=False)
                except Exception:
                    traceback.print_exc()
                    raise
        except Exception as error:
            raise RuntimeError(f"Local MLX execution failed ({type(error).__name__}); check the local environment"
                               + (" and the private log" if plan.log else "")) from None
        # generate_audio in mlx-audio 0.5.7 can catch errors internally and return.
        if not generated.is_file():
            raise RuntimeError("Local backend produced no WAV; check dependencies/model resources"
                               + (" in the private log" if plan.log else "; use --log for private diagnostics"))
        info = wav_info(generated)
        # The temporary file shares the output filesystem. link is exclusive,
        # unlike replace/rename, so a concurrent writer's output is preserved.
        os.link(generated, plan.output)
    return {"output": str(plan.output), **info, "backend": "local", "offline": True,
            "quality_assessed": False, "review_required": "Listen for identity, missing words, repetition and a complete ending"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="private/voice/voice-preferences.json")
    parser.add_argument("--text", required=True, help="UTF-8 complete narration file; relative to the working directory")
    parser.add_argument("--output", required=True, help="New WAV path; relative to the working directory")
    parser.add_argument("--language", default="Chinese")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--log", help="Optional new private log path; can contain narration and reference text")
    parser.add_argument("--check-only", action="store_true", help="Check configuration/local files without importing MLX or synthesizing")
    args = parser.parse_args(argv)
    try:
        plan = prepare_plan(args.config, args.text, args.output, language=args.language,
                            max_tokens=args.max_tokens, log_path=args.log)
        result = {"valid": True, "backend": "local", "model_loaded": False,
                  "audio_generated": False, "quality_assessed": False} if args.check_only else synthesize(plan)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, RuntimeError, UnicodeError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
