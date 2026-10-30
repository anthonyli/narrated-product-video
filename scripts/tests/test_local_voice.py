import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave


MODULE_PATH = Path(__file__).resolve().parents[1] / "local_voice.py"
SPEC = importlib.util.spec_from_file_location("local_voice", MODULE_PATH)
voice = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = voice
SPEC.loader.exec_module(voice)


def write_wav(path, frames=100):
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b"\x01\x00" * frames)


class LocalVoiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.voice_dir = self.root / "private" / "voice"
        self.voice_dir.mkdir(parents=True)
        self.model = self.root / "private" / "models" / "base"
        self.model.mkdir(parents=True)
        (self.model / "config.json").write_text("{}")
        (self.model / "model.safetensors").write_bytes(b"fixture, never loaded")
        write_wav(self.voice_dir / "reference.wav")
        (self.voice_dir / "reference.txt").write_text("private reference transcript", encoding="utf-8")
        self.text = self.root / "narration.txt"
        self.text.write_text("complete narration in one paragraph", encoding="utf-8")
        self.output = self.root / "work" / "raw.wav"
        self.config_path = self.voice_dir / "voice-preferences.json"
        self.config = {
            "backend": "local", "reference_audio": "reference.wav",
            "reference_text_file": "reference.txt", "preferred_voice": {"model": "../models/base"},
            "consent": {"authorized": True, "speaker": "self", "scope": "local_narration"},
        }
        self.save_config()

    def save_config(self):
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")

    def plan(self, **kwargs):
        return voice.prepare_plan(self.config_path, self.text, self.output, **kwargs)

    def test_resolves_config_paths_independently_of_working_directory(self):
        plan = self.plan()
        self.assertEqual(plan.model, self.model.resolve())
        self.assertEqual(plan.reference_audio, (self.voice_dir / "reference.wav").resolve())
        self.assertNotIn("private reference transcript", repr(plan))

    def test_check_only_does_not_import_backend_or_create_outputs(self):
        with patch.object(voice, "load_backend", side_effect=AssertionError("must not import")), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            result = voice.main(["--config", str(self.config_path), "--text", str(self.text),
                                 "--output", str(self.output), "--check-only"])
        self.assertEqual(result, 0)
        self.assertFalse(self.output.parent.exists())
        self.assertFalse(json.loads(output.getvalue())["audio_generated"])

    def test_rejects_cloud_and_unrecorded_consent(self):
        self.config["backend"] = "cloud"
        self.save_config()
        with self.assertRaisesRegex(ValueError, "no cloud fallback"):
            self.plan()
        self.config["backend"] = "local"
        for consent in [{}, {"authorized": "true", "speaker": "self", "scope": "local_narration"},
                        {"authorized": True, "speaker": "reference_style", "scope": "local_narration"}]:
            self.config["consent"] = consent
            self.save_config()
            with self.assertRaisesRegex(ValueError, "actual consent"):
                self.plan()

    def test_rejects_remote_absolute_tilde_or_missing_model(self):
        for model in ["https://example.invalid/model", "hf://org/model", "~/models/base", "/models/base", "org/missing"]:
            self.config["preferred_voice"]["model"] = model
            self.save_config()
            with self.assertRaises(ValueError):
                self.plan()

    def test_rejects_missing_reference_and_blank_texts(self):
        self.config["reference_audio"] = "absent.wav"
        self.save_config()
        with self.assertRaisesRegex(ValueError, "existing nonempty"):
            self.plan()
        self.config["reference_audio"] = "reference.wav"
        self.save_config()
        for path in [self.text, self.voice_dir / "reference.txt"]:
            previous = path.read_text()
            path.write_text(" \n")
            with self.assertRaisesRegex(ValueError, "blank"):
                self.plan()
            path.write_text(previous)

    def test_preserves_old_output_before_backend_import(self):
        self.output.parent.mkdir()
        self.output.write_bytes(b"old output")
        with self.assertRaises(FileExistsError):
            self.plan()
        self.assertEqual(self.output.read_bytes(), b"old output")

    def test_forces_offline_before_import_and_makes_one_continuous_call(self):
        calls = []
        def load_backend():
            self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
            self.assertEqual(os.environ["TRANSFORMERS_OFFLINE"], "1")
            def load_model(path):
                self.assertEqual(path, str(self.model.resolve()))
                return "loaded-local-model"
            def generate(**kwargs):
                calls.append(kwargs)
                print(kwargs["ref_text"])
                print(kwargs["text"])
                write_wav(Path(kwargs["file_prefix"] + ".wav"))
            return load_model, generate
        with patch.dict(os.environ, {"HF_HUB_OFFLINE": "0", "TRANSFORMERS_OFFLINE": "0"}), \
                patch.object(voice, "load_backend", side_effect=load_backend), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            result = voice.synthesize(self.plan())
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0]["join_audio"])
        self.assertIsNone(calls[0]["stt_model"])
        self.assertIsNone(calls[0]["voice"])
        self.assertEqual(calls[0]["speed"], 1.0)
        self.assertFalse(result["quality_assessed"])
        self.assertEqual(voice.wav_info(self.output)["frames"], 100)

    def test_upstream_swallowed_error_is_not_success(self):
        with patch.object(voice, "load_backend", return_value=(lambda _: object(), lambda **_: None)):
            with self.assertRaisesRegex(RuntimeError, "produced no WAV"):
                voice.synthesize(self.plan())
        self.assertFalse(self.output.exists())

    def test_bad_or_truncated_generated_wav_is_not_published(self):
        for data in [b"not audio", b"RIFF"]:
            def generate(**kwargs):
                Path(kwargs["file_prefix"] + ".wav").write_bytes(data)
            with patch.object(voice, "load_backend", return_value=(lambda _: object(), generate)):
                with self.assertRaises(ValueError):
                    voice.synthesize(self.plan())
            self.assertFalse(self.output.exists())
        sample = self.root / "truncated.wav"
        write_wav(sample)
        sample.write_bytes(sample.read_bytes()[:-10])
        with self.assertRaisesRegex(ValueError, "truncated"):
            voice.wav_info(sample)

    def test_concurrent_output_is_preserved(self):
        def generate(**kwargs):
            write_wav(Path(kwargs["file_prefix"] + ".wav"))
            self.output.write_bytes(b"concurrent writer")
        with patch.object(voice, "load_backend", return_value=(lambda _: object(), generate)):
            with self.assertRaises(FileExistsError):
                voice.synthesize(self.plan())
        self.assertEqual(self.output.read_bytes(), b"concurrent writer")

    def test_backend_exception_does_not_echo_private_text(self):
        def load_backend():
            raise RuntimeError("private reference transcript")
        with patch.object(voice, "load_backend", side_effect=load_backend):
            with self.assertRaises(RuntimeError) as caught:
                voice.synthesize(self.plan())
        self.assertNotIn("private reference transcript", str(caught.exception))

    def test_private_log_is_opt_in_exclusive_and_restrictive(self):
        log = self.root / "work" / "raw.log"
        def generate(**kwargs):
            print("private diagnostics")
            write_wav(Path(kwargs["file_prefix"] + ".wav"))
        with patch.object(voice, "load_backend", return_value=(lambda _: object(), generate)):
            voice.synthesize(self.plan(log_path=log))
        self.assertIn("private diagnostics", log.read_text())
        if os.name == "posix":
            self.assertEqual(log.stat().st_mode & 0o777, 0o600)
        self.output.unlink()
        with self.assertRaises(FileExistsError):
            self.plan(log_path=log)


if __name__ == "__main__":
    unittest.main()
