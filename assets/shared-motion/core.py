"""Deterministic scene timing and local encoding; no model, network or installer.

Adapters are trusted Python source selected explicitly by the author. A JSON
document is not a safe way to run untrusted adapter code.
"""
from dataclasses import dataclass
from pathlib import Path
import importlib.util
import json
import math
import os
import subprocess
import sys
import tempfile
import uuid
import wave


def finite(value, name, *, zero=False):
    try:
        valid = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be finite")
    if value < 0 if zero else value <= 0:
        raise ValueError(f"{name} must be {'nonnegative' if zero else 'positive'}")
    return value


@dataclass(frozen=True)
class Hold:
    at: float
    duration: float
    reason: str

    def __post_init__(self):
        finite(self.at, 'hold.at', zero=True)
        finite(self.duration, 'hold.duration')
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError('A hold needs a reading/narration reason')


@dataclass(frozen=True)
class Rest:
    """Replace an authored source resting interval; other source time is unchanged.

    Setting duration=0 removes it. This does not detect idle intervals: the
    adapter author must keep substantive motion and transitions outside them.
    """
    start: float
    end: float
    duration: float
    reason: str

    def __post_init__(self):
        finite(self.start, 'rest.start', zero=True)
        finite(self.end, 'rest.end')
        finite(self.duration, 'rest.duration', zero=True)
        if self.end <= self.start or not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError('Rest needs an ordered source interval and a reason')


@dataclass(frozen=True)
class Scene:
    id: str
    duration: float
    frame: object
    holds: tuple = ()
    rests: tuple = ()

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError('Scene id must be nonempty')
        finite(self.duration, 'scene.duration')
        if not callable(self.frame):
            raise ValueError('Scene.frame must be callable')
        previous = -1
        for hold in self.holds:
            if not isinstance(hold, Hold) or hold.at <= previous or hold.at >= self.duration:
                raise ValueError('Holds must be ordered, unique and inside source duration')
            previous = hold.at
        previous = -1
        for rest in self.rests:
            if not isinstance(rest, Rest) or rest.start < previous or rest.end > self.duration:
                raise ValueError('Rests must be ordered, nonoverlapping and inside source duration')
            if any(rest.start < h.at < rest.end for h in self.holds):
                raise ValueError('An inserted hold cannot be inside a replaced rest')
            previous = rest.end
        if self.total_duration <= 0:
            raise ValueError('A scene must retain some visible duration')

    @property
    def total_duration(self):
        return self.duration + sum(h.duration for h in self.holds) + sum(r.duration - (r.end-r.start) for r in self.rests)

    def source_time(self, t):
        finite(t, 'scene time', zero=True)
        if t >= self.total_duration:
            raise ValueError('Scene time must be before its exclusive end')
        source_cursor = 0
        events = sorted([(h.at, 0, h) for h in self.holds] + [(r.start, 1, r) for r in self.rests])
        for at, kind, event in events:
            untouched = at - source_cursor
            if t < untouched:
                return source_cursor + t
            t -= untouched
            if t < event.duration:
                return at if kind == 0 else event.start + t / event.duration * (event.end-event.start)
            t -= event.duration
            source_cursor = at if kind == 0 else event.end
        return source_cursor + t


class Episode:
    def __init__(self, scenes, width=1920, height=1080, fps=60):
        self.scenes = tuple(scenes)
        if not self.scenes or not all(isinstance(s, Scene) for s in self.scenes):
            raise ValueError('Episode needs Scene objects')
        if len({s.id for s in self.scenes}) != len(self.scenes):
            raise ValueError('Scene ids must be unique')
        for name, value in [('width', width), ('height', height), ('fps', fps)]:
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f'{name} must be a positive integer')
        if width % 2 or height % 2 or fps > 120:
            raise ValueError('Use even dimensions and fps <= 120')
        self.width, self.height, self.fps = width, height, fps

    @property
    def duration(self):
        return sum(s.total_duration for s in self.scenes)

    def frame(self, t):
        finite(t, 'episode time', zero=True)
        if t >= self.duration:
            raise ValueError('Episode time must be before its exclusive end')
        for scene in self.scenes:
            if t < scene.total_duration:
                return scene.frame(scene.source_time(t))
            t -= scene.total_duration
        raise ValueError('Time outside episode')


def reserve_publish(temporary, output):
    """Atomic, exclusive publish on one filesystem; never replace user files."""
    os.link(temporary, output)


def validate_audio(path, duration, fps):
    """Require measured continuous PCM WAV, including complete sample data."""
    finite(duration, 'audio target duration')
    finite(fps, 'fps')
    with wave.open(str(path), 'rb') as stream:
        rate, frames = stream.getframerate(), stream.getnframes()
        if frames <= 0 or rate <= 0 or stream.getcomptype() != 'NONE':
            raise ValueError('Audio must be nonempty PCM WAV')
        expected = frames * stream.getnchannels() * stream.getsampwidth()
        actual = 0
        while chunk := stream.readframes(65536):
            actual += len(chunk)
        if actual != expected:
            raise ValueError('Audio sample data is truncated')
        seconds = frames / rate
    if abs(seconds - duration) > 1 / fps + 1e-8:
        raise ValueError(f'Audio is {seconds:.4f}s but timeline is {duration:.4f}s; adjust semantic holds, not playback speed')
    return seconds


def load_episode(config_path, fps=None):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    if not isinstance(config, dict):
        raise ValueError('Config must be a JSON object')
    canvas = config.get('canvas', [1920, 1080])
    if not isinstance(canvas, list) or len(canvas) != 2:
        raise ValueError('canvas must be [width, height]')
    adapter = config.get('adapter')
    if not isinstance(adapter, str) or Path(adapter).is_absolute() or '://' in adapter:
        raise ValueError('adapter must be a relative path to trusted local Python source')
    source = (config_path.parent / adapter).resolve()
    if not source.is_file() or source.suffix != '.py':
        raise ValueError('Local adapter Python file is missing')
    # A fresh namespace keeps multiple episode configurations independent;
    # registration is required by dataclasses and other normal Python features.
    module_name = '_shared_motion_adapter_' + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(module_name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    scenes = module.create_scenes(config, config_path.parent)
    width, height = canvas
    return Episode(scenes, width, height, config.get('fps', 60) if fps is None else fps), config


def validate_render(episode, output, *, audio=None, start=0, end=None, preview_at=None):
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError('Output exists; choose a new versioned filename')
    if preview_at is not None:
        finite(preview_at, 'preview time', zero=True)
        if preview_at >= episode.duration or output.suffix.lower() != '.png':
            raise ValueError('Preview needs an in-range time and .png output')
    else:
        if output.suffix.lower() != '.mp4':
            raise ValueError('Video output must end in .mp4')
        end = episode.duration if end is None else end
        finite(start, 'clip start', zero=True)
        finite(end, 'clip end')
        if not 0 <= start < end <= episode.duration:
            raise ValueError('Clip must be inside the episode')
        if audio:
            validate_audio(audio, episode.duration, episode.fps)
    return output, end


def render(episode, output, *, ffmpeg='ffmpeg', audio=None, start=0, end=None, preview_at=None):
    output, end = validate_render(episode, output, audio=audio, start=start, end=end, preview_at=preview_at)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.shared-motion-', dir=output.parent) as temp:
        temporary = Path(temp) / output.name
        if preview_at is not None:
            frame = episode.frame(preview_at)
            if frame.size != (episode.width, episode.height):
                raise ValueError('Adapter frame dimensions differ from canvas')
            frame.save(temporary, format='PNG')
            frames = 1
        else:
            frames = max(1, math.ceil((end - start) * episode.fps - 1e-8))
            command = [str(ffmpeg), '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                       '-s', f'{episode.width}x{episode.height}', '-r', str(episode.fps), '-i', '-']
            if audio:
                command += ['-ss', str(start), '-i', str(Path(audio).resolve()), '-map', '0:v:0', '-map', '1:a:0',
                            '-c:a', 'aac', '-ar', '48000', '-b:a', '192k']
            else:
                command += ['-an']
            command += ['-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
                        '-t', str(frames / episode.fps), '-movflags', '+faststart', str(temporary)]
            with open(Path(temp) / 'encode.log', 'w+b') as log:
                process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
                try:
                    for index in range(frames):
                        frame = episode.frame(start + index / episode.fps)
                        if frame.size != (episode.width, episode.height):
                            raise ValueError('Adapter frame dimensions differ from canvas')
                        process.stdin.write(frame.convert('RGB').tobytes())
                    process.stdin.close()
                    if process.wait() != 0:
                        raise RuntimeError('FFmpeg encoding failed')
                except BaseException:
                    if process.poll() is None:
                        process.terminate()
                    process.wait()
                    log.seek(0)
                    diagnostic = log.read().decode('utf-8', errors='replace')[-2000:]
                    if diagnostic:
                        print(diagnostic)
                    raise
        reserve_publish(temporary, output)
    return {'output': str(output), 'fps': episode.fps, 'frames': frames,
            'duration': None if preview_at is not None else frames / episode.fps,
            'canvas': [episode.width, episode.height], 'audio': bool(audio),
            'burned_narration_subtitles': False, 'quality_assessed': False}
