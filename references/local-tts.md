# 本地口播：Qwen3-TTS + MLX（默认优先）

需要生成或替换配音时使用本流程。已有录制视频仍默认保留原声。本地环境不满足时先说明缺项，不自动调用百炼。

## 平台与参考地址

- 技能源码：[anthonyli/narrated-product-video](https://github.com/anthonyli/narrated-product-video)。
- 推理工具：[mlx-audio](https://github.com/Blaizzy/mlx-audio)，以下示例面向 Apple Silicon Mac，使用 Python 3.10+。
- 模型：[mlx-community/Qwen3-TTS-12Hz-1.7B-Base-4bit](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-Base-4bit)，用于参考声音合成。下载前查看模型页的当前文件大小，另为运行时内存和输出预留空间；4-bit 不代表所有机器都能流畅运行。
- 其他平台：[Qwen3-TTS 官方项目](https://github.com/QwenLM/Qwen3-TTS)提供原始模型与 Python 用法。Windows／Linux／Intel Mac 需按上游要求另配环境，不能直接使用这里的 MLX 权重和命令；本技能尚未验证这些平台的完整流程。

## 1. 在制作项目中准备环境

以下命令从当前制作项目根目录执行。技能安装目录只提供规则、脚本与模板，不存放使用者的模型、虚拟环境或声音。先确认 `python3 --version` 满足要求。

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install mlx-audio huggingface_hub soundfile
mkdir -p private/models private/voice work/local-tts
hf download mlx-community/Qwen3-TTS-12Hz-1.7B-Base-4bit \
  --local-dir private/models/Qwen3-TTS-12Hz-1.7B-Base-4bit
python -m pip freeze > work/local-tts/environment.txt
```

安装与下载需要网络；这些命令不调用云端语音合成服务。模型权重、分词器及音频编解码资源应完整下载，实际依赖以安装版本为准。现有环境可复用，不必重复下载。新建制作项目时，将 `.venv/`、`private/`、`work/`、`outputs/` 加入该项目的 `.gitignore`。

## 2. 准备使用者自己的声音

将清晰、无伴奏、单人说话且有使用授权的短录音放到 `private/voice/reference.wav`，准确转写保存为 `private/voice/reference.txt`。文字必须对应这份录音，不是待生成的口播稿。不要沿用作者的录音、私人 voice ID 或个人路径。

在 `private/voice/voice-preferences.json` 中记录：

```json
{
  "backend": "local",
  "reference_audio": "reference.wav",
  "reference_text_file": "reference.txt",
  "preferred_voice": {
    "model": "../models/Qwen3-TTS-12Hz-1.7B-Base-4bit",
    "model_id": "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-4bit"
  },
  "service_constraints": ["优先本地合成，不自动切换云端"]
}
```

已有配置应合并所需字段，不覆盖个人声音偏好。配置内文件路径相对配置所在目录；下方示例按此规则解析。这个配置由 Agent／示例代码读取，上游 mlx-audio 不会自动读取它。授权状态按真实情况记录，不从示例自动推定。

## 3. 生成连续口播

先将完整口播写入 `work/local-tts/narration.txt`，首次用短段落检查环境和声音，再生成全文。下例使用显式参考转写，避免因缺少转写而额外加载识别模型；运行时使用本地模型路径并启用离线模式。已有输出时换新文件名，保留旧版本。

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python - <<'PY'
import json
from pathlib import Path
import soundfile as sf
from mlx_audio.tts.utils import load_model
from mlx_audio.tts.generate import generate_audio

config_path = Path("private/voice/voice-preferences.json")
config = json.loads(config_path.read_text(encoding="utf-8"))
resolve = lambda value: str((config_path.parent / value).resolve())
output = Path("work/local-tts/raw.wav")
if output.exists():
    raise FileExistsError(f"保留旧版本，请更换输出路径：{output}")
text = Path("work/local-tts/narration.txt").read_text(encoding="utf-8").strip()
reference_text = Path(resolve(config["reference_text_file"])).read_text(encoding="utf-8").strip()
if not text or not reference_text:
    raise ValueError("口播稿和参考录音转写均不能为空")
output.parent.mkdir(parents=True, exist_ok=True)
model = load_model(resolve(config["preferred_voice"]["model"]))
generate_audio(
    model=model,
    text=text,
    ref_audio=resolve(config["reference_audio"]),
    ref_text=reference_text,
    lang_code="Chinese",
    file_prefix=str(output.with_suffix("")),
    audio_format="wav",
    join_audio=True,
)
info = sf.info(str(output))
if info.frames <= 0:
    raise RuntimeError("没有生成有效音频")
print(f"已生成 {output}，时长 {info.duration:.2f} 秒；仍需审听")
PY
```

这是调用上游库的示例，不是仓库自带的一键 TTS 命令。接口以安装版本和[上游合成入口](https://github.com/Blaizzy/mlx-audio/blob/main/mlx_audio/tts/generate.py)为准；版本变化时先核对参数。若离线运行缺资源，检查缺失的依赖／模型文件，补齐后重试，不能把失败视为云端调用许可。首轮自动检查通过后仍需审听音色、漏词、重复、尾音与停顿。

长稿优先连续合成，受内存或生成长度限制时按完整语义段拆分；检查末句是否完整，不能把截断的输出当成成功。百炼的 600 字限制不适用于此本地流程。

## 字幕与后处理

本地 TTS 生成 WAV，不自动提供本技能所需的词级时间戳。选择可输出词时间戳的本地 ASR／对齐工具，对原始 `raw.wav` 识别；需要独立下载其模型并验证离线运行。当前仓库没有统一的本地 ASR 安装或转换脚本，Agent 需根据所选工具适配，不能声称以上合成步骤已完成字幕。

`scripts/align_captions.py` 接受如下嵌套结构，`begin_time`／`end_time` 单位为毫秒；把实际识别的所有词写入 `words`，不要用示例时间或按字数平均分配代替识别结果：

```json
{"transcriptions":[{"transcripts":[{"sentences":[{"words":[
  {"text":"你好","begin_time":100,"end_time":500}
]}]}]}]}
```

随后按主技能用 `audio_timing.py` 处理响度、速度与必要静音，并用新的时间映射运行 `align_captions.py`。脚本位于技能目录的 `scripts/`；从独立制作项目调用时使用实际技能目录路径，不假设制作项目自带这些脚本。对原稿与识别的差异先核实声音，再纠正识别错误或重合成受影响段落。

仅完成本地配音不等于整个视频流程离线。云端识别、素材获取等各有网络需求；没有当前任务的云端授权，不执行百炼的声音注册、合成或时间戳请求。首次安装和新平台的完整运行仍需实际验证。
