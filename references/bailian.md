# 百炼口播与词时间戳

端点默认 https://dashscope.aliyuncs.com/api/v1；密钥、模型、声音必须属于匹配区域。凭据读取环境变量 DASHSCOPE_API_KEY，模型变化时核对官方文档。

以下命令从当前项目根目录执行。声音偏好在 `private/voice/voice-preferences.json`，其中素材路径相对该文件所在目录；已有兼容声音响应保存在 `private/voice/bailian-voice.json`。先检查项目内响应及声音与模型的匹配关系，不依赖个人主目录或旧项目的位置。兼容声音可从响应的 `output.voice` 或缓存包装的 `response.output.voice` 读取并注入子进程，不打印到共享日志。`private/` 应被 Git 忽略。

已授权且没有兼容声音时注册：
```sh
python scripts/bailian_voice.py enroll --reference private/voice/own-voice-reference.wav --output private/voice/bailian-voice.json
```
使用清晰、无伴奏、无重叠说话的样本。默认目标模型 qwen3-tts-vc-2026-01-22；声音注册与合成模型必须匹配。不要把样本打包到技能。

把完整稿保存为 UTF-8 文本。VOICE_ID 必须来自当前账号私有响应，已有兼容声音直接复用。
```sh
python scripts/bailian_voice.py synthesize --text work/narration.txt --voice "$VOICE_ID" --output work/tts-private.json --audio work/raw.wav
python scripts/audio_timing.py work/raw.wav --output work/narration.wav --map work/timing-map.json --speed 1.12
python scripts/bailian_voice.py align-submit --tts-response work/tts-private.json --output work/asr-task-private.json
python scripts/bailian_voice.py align-fetch --task work/asr-task-private.json --output work/alignment-private.json
python scripts/align_captions.py --alignment work/alignment-private.json --text work/narration.txt --map work/timing-map.json --output work/captions.json
```

单次限制 600 字，超过按自然段分组，不能逐句合成。异步识别使用 qwen3-asr-flash-filetrans 与 enable_words。align-fetch 等待时退出码 3，稍后查询同一个任务，不重复提交。

付费操作有输入哈希缓存，同输入复用成功结果，不同输入用新路径。结果不明时 .pending 阻止自动重试；核实服务端状态后再处理，不能直接删标记循环请求。响应中的临时 URL 私有保存，需在过期前下载。

官方文档：
- [声音复刻](https://help.aliyun.com/zh/model-studio/voice-cloning-user-guide)
- [声音复刻 HTTP](https://help.aliyun.com/zh/model-studio/voice-clone-design-http-api)
- [语音合成 API](https://help.aliyun.com/zh/model-studio/qwen-tts-api)
- [录音识别与时间戳](https://help.aliyun.com/zh/model-studio/recording-file-recognition-qwen)

错误先检查 HTTP、服务错误码、区域、模型及声音匹配；不要把完整敏感响应或带签名 URL 输出到共享日志。
