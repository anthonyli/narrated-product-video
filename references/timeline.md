# 时间轴

路径相对 JSON 所在目录。以下仅格式示例，实际秒数必须来自处理后的声音与词时间戳：
```json
{
  "aspect": "16:9",
  "fps": 24,
  "audio": "narration.wav",
  "font": "/path/to/installed-cjk-font.ttf",
  "font_size": 36,
  "shots": [
    {"start": 0, "end": 2.3, "image": "shot-01.png"},
    {"start": 2.3, "end": 5.0, "image": "shot-02.png"}
  ],
  "captions": [
    {"start": 0.2, "end": 2.1, "text": "这是第一句口播。"},
    {"start": 2.4, "end": 4.8, "text": "这是第二句口播。"}
  ]
}
```
每个镜头首尾相接，最后一个结束于音轨实际末尾。图像可淡化，音频不能按镜头切开。字幕来自 align_captions.py 的 captions；characters 可定位镜头对应词。

```sh
python scripts/render_video.py work/timeline.json --output outputs/tutorial-16x9.mp4
```

同时输出同名 SRT。16:9 → 1920×1080，4:3 → 1440×1080，3:4 → 1080×1440。每种比例需要独立重排的图片与时间轴。竖版用上下结构，横版用左右结构，字幕避开按钮。

验收：
- ffmpeg -v error -i outputs/tutorial-16x9.mp4 -f null - 完整解码。
- ffprobe 或 FFmpeg 信息核对分辨率、帧率、音轨、时长。
- 封面比例用整数乘法验证，例如 4:3 满足 width*3 == height*4。
- 查看首帧、操作点和结尾，确认没有黑屏、切字或字幕遮挡。
- timing-map.json 记录静音与时长。静音检测不代表主观听感。
- 核对识别与原稿，字幕不重叠且末句完整。多段拼接检查所有接点。
