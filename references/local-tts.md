# 本地口播：Qwen3-TTS + MLX（默认优先）

需要生成或替换配音时使用本流程。已有录制视频仍默认保留原声。本地环境不满足时先说明缺项，不自动调用百炼。

## 平台与参考地址

- 技能源码：[anthonyli/narrated-product-video](https://github.com/anthonyli/narrated-product-video)。
- 推理工具：[mlx-audio](https://github.com/Blaizzy/mlx-audio)，以下命令面向 Apple Silicon Mac，使用 Python 3.10+。
- 模型：[mlx-community/Qwen3-TTS-12Hz-1.7B-Base-4bit](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-Base-4bit)，用于参考声音合成。下载前查看模型页的当前文件大小，另为运行时内存和输出预留空间；4-bit 不代表所有机器都能流畅运行。
- 其他平台：[Qwen3-TTS 官方项目](https://github.com/QwenLM/Qwen3-TTS)提供原始模型与 Python 用法。Windows／Linux／Intel Mac 需按上游要求另配环境，不能直接使用这里的 MLX 权重和命令；本技能尚未验证这些平台的完整流程。

## 1. 在制作项目中准备环境

以下命令从当前制作项目根目录执行。技能安装目录只提供规则、脚本与模板，不存放使用者的模型、虚拟环境或声音。先确认 `python3 --version` 满足要求。

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "mlx-audio==0.5.7" huggingface_hub
mkdir -p private/models private/voice work/local-tts
hf download mlx-community/Qwen3-TTS-12Hz-1.7B-Base-4bit \
  --local-dir private/models/Qwen3-TTS-12Hz-1.7B-Base-4bit
python -m pip freeze > work/local-tts/environment.txt
```

参考环境固定为已验证公共接口的 `mlx-audio==0.5.7`；其他版本先核对接口并做短句实测。安装与下载需要网络；这些命令不调用云端语音合成服务。模型权重、分词器及音频编解码资源应完整下载，实际依赖以安装版本为准。现有环境可复用，不必重复下载。新建制作项目时，将 `.venv/`、`private/`、`work/`、`outputs/` 加入该项目的 `.gitignore`。

## 2. 准备使用者自己的声音

将清晰、无伴奏、单人说话且有使用授权的录音转成 PCM WAV，放到 `private/voice/reference.wav`，准确转写保存为 `private/voice/reference.txt`。文字必须对应这份录音或实际选取的片段，不是待生成的口播稿。不要沿用作者的录音、私人 voice ID 或个人路径。保留原始文件，转换时不用降噪或变速改变音色；若使用 FFmpeg，先发现本机可用路径，用 `-n` 保留已有文件。

在 `private/voice/voice-preferences.json` 中记录：

```json
{
  "backend": "local",
  "reference_audio": "reference.wav",
  "reference_text_file": "reference.txt",
  "consent": {
    "authorized": false,
    "speaker": "self",
    "scope": "local_narration"
  },
  "preferred_voice": {
    "model": "../models/Qwen3-TTS-12Hz-1.7B-Base-4bit",
    "model_id": "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-4bit"
  },
  "service_constraints": ["优先本地合成，不自动切换云端"]
}
```

已有配置应合并所需字段，不覆盖个人声音偏好。配置内路径必须相对配置所在目录；可引用已存在的模型目录，不复制大模型进技能。`model_id` 只记录来源，脚本不把它作为下载地址。

示例的 `authorized: false` 是待填写状态。只有已获得本人或声音权利人的授权时，才据实设为 `true`；`speaker` 使用 `self` 或 `authorized_speaker`，本工具的范围为 `local_narration`。用户在当前对话中已经说明是本人声音并要求使用，就记录该现有授权，无需再问。参考风格不等于授权复刻音色。此配置、参考音频、转写及原始文件留在制作项目的私有目录，不进入公开 skill。

## 3. 检查与生成连续口播

先将完整口播写入 `work/local-tts/narration.txt`。从制作项目根目录调用技能内的 `scripts/local_voice.py`；下面的 `SKILL_DIR` 应设置为实际技能目录，不是制作项目。工具不安装依赖或下载模型，也不调用云端服务。

```sh
# 只检查配置、授权记录、本地模型与声音文件；不导入 MLX、不生成声音。
python "$SKILL_DIR/scripts/local_voice.py" \
  --text work/local-tts/narration.txt \
  --output work/local-tts/raw-v1.wav \
  --check-only

# 首次用短段落试听，再用完整稿合成；已有输出请更换版本名。
python "$SKILL_DIR/scripts/local_voice.py" \
  --text work/local-tts/narration.txt \
  --output work/local-tts/raw-v1.wav
```

默认读取 `private/voice/voice-preferences.json`，其他配置用 `--config` 指定。命令行的配置、稿件和输出路径相对执行目录；配置内部的模型、声音、转写路径相对配置文件。参考音频必须为可完整读取的 PCM WAV。`--check-only` 只确认本地文件和授权字段，不证明模型能加载、转写准确或声音可用。

工具在导入 MLX 前强制 `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`，只向上游传入已存在的本地模型目录和显式参考转写，并禁用自动 ASR、播放与流式输出。它把完整稿一次交给 `generate_audio(..., join_audio=True)`，不按字幕切段；生成原声速度为 1.0，后处理另用 `audio_timing.py`。默认 `--language Chinese`、`--max-tokens 4096`；token 上限不能证明全文已读完，需检查末句。长稿受内存或生成长度限制时按完整语义段拆分；百炼的 600 字限制不适用于本地流程。

代码按本机 `mlx-audio 0.5.7` 的公共 `load_model`／`generate_audio` 接口实现，WAV 检查使用标准库，不额外依赖 `soundfile`。兼容性以安装版本和[上游合成入口](https://github.com/Blaizzy/mlx-audio/blob/main/mlx_audio/tts/generate.py)为准。上游可能捕获内部错误后正常返回，因此工具必须读完实际生成的 WAV、确认采样数据完整，才把它发布到目标路径；已有文件以及并发创建的输出都不会被覆盖。

上游即使关闭详细输出也可能打印文案，工具默认屏蔽这些日志。排查失败时可显式加 `--log work/local-tts/raw-v1.log`；日志以私有权限创建，可能包含口播或参考转写，禁止随 skill、公开交付包上传。日志路径也必须是新文件。工具不会自动重试或切换到百炼、系统声音及另一音色。离线缺资源时报告具体缺项；安装、模型下载和网络授权另行处理，不改动安全配置。

自动检查通过后仍需审听音色、漏词、重复、尾音与停顿，并用本地 ASR 检查完整稿。返回的 `quality_assessed: false` 表示尚未完成这些评价。没有实际成功的声音文件时，不能把环境检查、配置保存或命令成功启动当成已完成本人声音口播。

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
