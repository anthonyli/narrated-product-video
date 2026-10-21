# GSAP 动效路径（借助「五鼎动画工厂」技能）

当用户要求「像 demo 那样的动感」「MG 动画」「弹性动效」「知识动画」，且画面以**动画表达为主、不依赖真实产品截图**时，用这条路径。它与 `scenes` 编辑排版路径的分工：

| | editorial scenes（本技能 Remotion） | GSAP 动效（五鼎动画工厂） |
|---|---|---|
| 强项 | 真实截图进浏览器窗框、来源标注、证据排版 | elastic/back 弹入、逐字上滑、打字机、图标描边——手 K 级 MG 动感 |
| 适用 | 产品宣传、教程解说（有截图素材） | 概念讲解、要点罗列、金句片（无截图也能饱满） |
| 字幕/配音 | 内置字幕条 + bailian 声音 | 用它的 TTS 工作流（edge-tts），或本技能出声音后 ffmpeg 混音 |

两者可组合：GSAP 出动画主体，本技能负责口播稿、字幕校对与最终混音验收。

## 本机（macOS）已验证的调用方式

技能装在 `~/.workbuddy/skills/wuding-kinetic-video/`（下称 `$SK`）。作者按 Windows 写死了路径，Mac 上按以下参数覆盖（2026-10-11 全链路冒烟验证通过，样例在 `work/gsap-smoke/`）：

```bash
SK=~/.workbuddy/skills/wuding-kinetic-video
CHROME="/Users/anthonyli/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
FF=<项目内或 imageio-ffmpeg 的 ffmpeg 路径>   # 不能用 Playwright 自带 ffmpeg（缺 H.264）

# 1. 读稿拆幕写 scenes.json（schema 见 $SK/references/scenes_schema.md）
# 2. 构建 HTML
NODE_OPTIONS= /usr/local/bin/node $SK/scripts/build_html.mjs scenes.json out.html
# 3. 抽帧验证（先看帧再全量）
NODE_OPTIONS= /usr/local/bin/node $SK/scripts/render.mjs out.html _preview --chrome="$CHROME" --only=0,90,180,270
# 4. 全量渲染（长片用 --start/--end 分段）
NODE_OPTIONS= /usr/local/bin/node $SK/scripts/render.mjs out.html _frames --chrome="$CHROME"
# 5. 编码
NODE_OPTIONS= /usr/local/bin/node $SK/scripts/encode.mjs _frames final.mp4 --ffmpeg=$FF
# 6.（可选）TTS 配音
/Users/anthonyli/.workbuddy/binaries/python/envs/default/bin/python $SK/scripts/tts_scenes.py script.json scenes.json vo --ffmpeg=$FF
```

注意事项：

- **一律加 `NODE_OPTIONS=`**（清空沙箱 fs shim，否则报假 EEXIST，与 Remotion 同一坑）。
- playwright-core 装在 `~/.workbuddy/binaries/node/workspace/node_modules`，render.mjs 会自动解析到；缺失时 `npm install playwright-core` 到该目录。
- 渲染是 seek 确定性的（`window.__KINETIC__.seek(t)`），机器慢不掉帧；帧目录 `_frames`/`_preview` 约 200MB，交付后可删。
- **不要改动 `$SK` 内的文件**——它是市场安装的技能，更新会被覆盖；Mac 适配全部通过命令行参数完成。

## 该技能的三个自带行为（用前知晓）

1. **文案替换**：`tts_scenes.py` 会把稿中「中老年人/银发族」等词替换成作者的口癖（"爱折腾的哥哥姐姐"）；给本用户做视频时 unwanted，用本技能的 bailian 声音替代其 TTS，或检查替换逻辑。
2. **默认角标**是「你的品牌 × 老歌哥」，`badge` 字段必须改成用户自己的品牌或留空。
3. 默认皮肤 `tech`（深墨+薄荷绿）；要贴合 PageOn 纸白品牌风时改 `skin` 或在 `free` 幕自定义。

## 质量基线（沿用本技能标准）

分镜节奏参照 editorial-explainer 的量化基线（旁白 410–440 字/分、章节 20–40s、每幕 4–8s）；bars 数值必须真实或标注估算；交付前抽帧确认无文字溢出（`check_overflow.mjs`）。
