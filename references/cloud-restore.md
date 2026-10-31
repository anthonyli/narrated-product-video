# 在新的云电脑恢复制作能力

本节针对用户要求的 Linux 云端制作，不需要连接用户的 Mac。云工作目录、已下载模型与缓存可能随执行环境替换而丢失；保存源码包不等于模型和私有声音会永久驻留，也不等于已配置好每日调度。

## 每次运行前

1. 从已确认的版本源码包恢复 skill 到工作目录，核对包内清单。不要依赖个人 Mac 路径，也不要在恢复时直接运行未知适配器。
2. 检查 Python、FFmpeg（libx264、libass）、中文字体、可用内存与磁盘。模型加载、ASR与渲染分开安排，避免在有限内存下并发重任务。
3. 按 [local-tts.md](local-tts.md#linux-cloud-computer-offline-cpu-backend) 的固定依赖与模型版本恢复隔离环境；网络下载依赖当前授权，不自动接入收费语音服务。已经存在的缓存先核验再复用。
4. 在**制作项目**的 `private/voice/` 中恢复用户已授权参考声音和真实转写，按下方示例建立相对路径配置。私有素材独立保管、通过受支持的文件流恢复，不加入源码包或公开视频包。
5. 用 `local_voice.py --check-only` 验证配置；再实际生成一小段新声音，并完成PCM解码与本地ASR。环境检查通过不能代替实际合成验证；新环境音色与语速仍需审听。
6. 从完整口播生成正式声音，根据实际词时间戳、处理映射排画面与字幕；运行实际动画、字幕、完整解码与代表帧检查。保存当前提交/补丁、依赖、模型版本、参数、时长与验证记录。

## 私有声音配置示例（不含真实声音）

以下示例中的 `authorized: false` 不是已有授权记录。只有确认当前用户和当前用途已获授权，才据实记录为 `true`。`local_narration` 指当前执行电脑上的离线推理，不是第三方语音API。

```json
{
  "backend": "local",
  "engine": "qwen-pytorch-cpu",
  "consent": {"authorized": false, "speaker": "self", "scope": "local_narration"},
  "preferred_voice": {"model": "../../models/qwen3-tts-0.6b"},
  "reference_audio": "reference.wav",
  "reference_text_file": "reference.txt"
}
```

配置保存为制作项目 `private/voice/voice-preferences.json`，模型保存在制作项目 `models/qwen3-tts-0.6b`，实际路径按恢复位置调整。不能借示例授权字段替代真实许可。用无损PCM WAV参考，并核对转写；旧 Mac 成片的音轨不能冒充本次云端新生成语音。

## 验证与交付

```sh
python -m unittest discover -s "$SKILL_DIR/scripts/tests" -v
python -m unittest discover -s "$SKILL_DIR/assets/shared-motion/tests" -v
```

单元测试不会评估审美、音色或真人语音授权。最终保留MP4、独立SRT/音轨/稿件、封面与发布文案；源码包排除`.git`、依赖环境、模型权重、声音样本、私有配置、日志与生成视频。新环境不能用旧测试报告冒充本次实跑，也不能承诺无人值守永远不需要恢复资源。

## CPU voice startup privacy requirement

Use `PYTHON=.venv-cloud-tts/bin/python scripts/run_cpu_voice.sh --segments ...`
instead of directly invoking Python. The launcher sets official
`ORT_DISABLE_TELEMETRY=1` **before Python starts**, plus HF/Transformers offline
flags. The original API-only disabling was rejected because telemetry was still
attempted. See `local-tts.md` for exact validation evidence and limits; a successful
short test does not mean all future network traffic has been audited.


## 云端 v3 验收补强

恢复 v3 源码后，读 `references/acceptance.md`。配音、渲染核心和旧审计接口未改；新增主画面低变化扫描、验收证据/成片哈希门禁与回归测试。恢复包不含已生成项目、用户声音或模型，测试通过不等于本次成片通过。
