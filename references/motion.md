# Remotion＋FFmpeg 动态信息层

用于「跟着说话，页面有提示」的默认动画流程。时间轴由口播意义与最终声音共同决定。Remotion 负责逐帧动画、视频布局、字幕和信息层；FFmpeg 负责同步粗剪、音频处理、压制及验证。此模板提供基础组件，品牌风格和复杂图表可在任务副本扩展。

## 选择路线与时间轴接口

- 录屏、真人口播的叠加提示，以及既有 4:3／3:4 布局，使用本文的 `overlays` 接口。
- 编辑式信息场景可使用 `scenes` 接口，具体字段、可运行示例和检查命令见 [editorial-scenes.md](editorial-scenes.md)。当前实现限 16:9，提供概念、比较、流程、数量图和多状态示意。真实截图、图表或明确标识的示意按解释任务选择；不要求每个场景都套浏览器窗框。不要将旧 `videoBox`、`cardBox` 或非空 `overlays` 混入该接口。
- 同一对象连续重排、聚焦、变形和跨镜头迁移，采用 [shared-motion.md](shared-motion.md)。它是独立路线，不把其字段直接塞入 Remotion `scenes`。保留已认可的源码、配色和对象身份，按实际实现调整时序。
- Anatomy 使用其独立适配流程。第三方 GSAP 仅为可选工具，见 [gsap-motion.md](gsap-motion.md)。比例不强制决定渲染器，现有接口不能覆盖的表达应在任务副本扩展并实渲验证。
- 下文的组件、JSON 与命令仅适用于 Remotion 模板。两种 Remotion 接口共享连续音轨约定；共享元素路线默认不烧录口播字幕，按该路线文档独立保存稿件与对齐结果。分镜记录与渲染参数分开，不能凭空添加 JSON 字段。

## 编辑与动画规则

- 按视觉分类组织画面：人物口播保持人物可见，可按空间安排侧边或上下卡片；全屏实录演示保持操作画面可读；知识解说型 MG 动画执行 [editorial-explainer.md](editorial-explainer.md)，可按观点组织窗口、图表和纸感拼贴。基础模板默认 contain 保护完整画面；如需 cover 或推近，先抽帧检查头、手和关键内容。给信息层留空间，不默认遮挡人物或操作区。
- 需要烧录字幕时，仅显示当下短字幕，约 10–22 个中文字、最多两行。关键词、卡片不重复整句字幕，同一时刻通常一个主重点，进度条可并存。
- 新章节使用 big-title，通常 1.5–3 秒；普通卡片通常保留 2–5 秒，复杂截图或代码更长。触发点取对应词时间，入场可提前约 0.1 秒以便读懂；根据语义退出。
- 强调词在说到时改变颜色或底色。tokens 使用实际词边界；逐字边界若由词区间插值，标明估算并抽查，不能宣称精确。标点和空格仍保留在字幕文本中。
- 卡片入场约 0.2–0.4 秒，离场约 0.15–0.25 秒，统一缓动。按语义需要安排 1–3% 推近、轻微位移或信息切换，避免每个镜头机械等待同样的秒数；适合阅读的静止时段应保留。连续推近段的 from/to 要接续，不能突然跳回原缩放。
- 动画用 useCurrentFrame、interpolate、spring 计算，不能依赖实时计时器、随机值或 CSS animation，否则不同渲染帧可能不一致。
- 不编造数据、证言和截图。browser 需要真实截图素材，示意图标明“示意”。code 只放能读懂的关键几行，复杂 diagram 使用生成并核实的 SVG／图片或扩展组件。
- 每种比例独立检查 videoBox、cardBox、字幕与平台按钮安全区；不要只改 aspect 就声称已经验收三种布局。

## 组件约定

| type | 必要内容 | 基础效果 |
| --- | --- | --- |
| big-title | text | 大标题弹入，用于章节和观点 |
| keyword | text | 强调色关键词 |
| bullet-list | text, items（1–3 项） | 要点错峰出现 |
| number | text, value, 可选 unit | 大数字卡片，保留原始数值 |
| quote | text, 可选 attribution | 金句卡片 |
| comparison | text, left/right 的 title、text | 左右两栏对照 |
| browser | text, image | 浏览器式截图卡片 |
| code | text, code（最多 8 行） | 等宽代码卡片 |
| diagram | text, items（1–3 项） | 简单纵向步骤箭头；复杂图另做 |
| progress | text | 当前章节内的进度条 |

卡片可带 label、detail、box。图标可以放在已准备的图片中，或在任务副本引入本地图标组件；基础模板不依赖在线图标请求。以上为可运行基础组件，不等于完整的二期品牌组件库。

## 时间轴

这是格式示例，实际所有秒数来自最终声音。路径相对 JSON 文件。已有视频的 video 与 audio 必须来自同次粗剪；video 在模板中静音，audio 只播放一次。仅配音场景可用 image 或无视频的背景，脚本不会自行生成素材或识别口误。

```json
{
  "aspect": "16:9",
  "fps": 30,
  "duration": 6,
  "video": "edit-v1/master.mov",
  "audio": "edit-v1/narration.wav",
  "accent": "#77efca",
  "videoFit": "contain",
  "videoBox": [0.045, 0.14, 0.5, 0.64],
  "cardBox": [0.59, 0.2, 0.365, 0.52],
  "captions": [
    {"start": 0.2, "end": 2.5, "text": "先找到真正的问题。", "tokens": [
      {"start": 0.2, "end": 1, "text": "先找到"},
      {"start": 1, "end": 1.7, "text": "真正的"},
      {"start": 1.7, "end": 2.5, "text": "问题。", "highlight": true}
    ]},
    {"start": 3, "end": 5.5, "text": "再分成三个步骤。"}
  ],
  "overlays": [
    {"type": "progress", "start": 0, "end": 6, "text": "01 / 问题"},
    {"type": "big-title", "start": 0.2, "end": 2.6, "text": "问题", "detail": "先明确要解决什么"},
    {"type": "bullet-list", "start": 3, "end": 6, "text": "怎么解决", "items": ["定位", "验证", "行动"]}
  ],
  "motions": [
    {"start": 0, "end": 3, "from": 1, "to": 1.02},
    {"start": 3, "end": 6, "from": 1.02, "to": 1}
  ]
}
```

`duration` 为实际最终音频时长，渲染向上取整到帧；差值应小于一帧。每个字幕和信息层的 start/end 都必须在此范围内。box 是画布中的 `[x, y, width, height]`，各值为 0–1。人物在右时调换 videoBox/cardBox。跨机器复用时，将有使用权限的字体放入项目 `private/fonts/`，由 `fontFile` 相对时间轴 JSON 引用，例如 `work/task/motion.json` 使用 `../../private/fonts/cjk.ttf`；项目未附带该示例字体。不指定字体时使用运行环境的字体回退，不能据此保证跨机器排版一致。

`tokens` 可省略，省略时显示普通字幕；提供时拼接文本必须与字幕完全一致，含标点。用 align_captions.py 的结果时 captions 可直接复用，characters 不能冒充真实逐字标注。渲染器只读取制作好的时间轴，不会从主题自动推断词时间。

## 运行

从当前项目根目录运行。`SKILL_DIR` 是规则与模板来源目录，由执行环境发现；在本仓库直接使用时可设为 `.`。所有 `work/`、`private/`、`outputs/` 路径仍相对当前项目，不相对外部技能安装目录。各 Remotion 包固定同版本，升级后重新实渲验证。

```sh
mkdir -p work/task
cp -R "$SKILL_DIR/assets/remotion" work/task/remotion
npm ci --prefix work/task/remotion --no-fund --no-audit
node work/task/remotion/render.mjs work/task/motion.json outputs/video-v1.mp4 --validate-only
node work/task/remotion/render.mjs work/task/motion.json outputs/video-v1.mp4
```

渲染器验证时间、素材存在性及基础内容，输出 MP4 与同名 SRT，拒绝覆盖；素材复制到临时目录供离屏渲染，结束后清理。首次运行可能下载 Remotion 所需的浏览器内核；这用于离屏渲染。已有兼容可执行文件可通过 REMOTION_BROWSER_EXECUTABLE 指定，不写死个人路径。模板随附 package-lock.json，使用 npm ci 安装锁定依赖；任务副本中的锁文件应随工程保留。

## 验收

- FFmpeg 完整解码 MP4；检查尺寸、帧率、H.264/yuv420p、AAC、48 kHz，视频与最终 WAV 时差不超过一帧或已解释的编码延迟。
- 检视每种卡片入场中间帧和稳定帧，以及字幕较长处、所有剪辑接点、首尾。确认中文正常、没有遮挡人物、截字或卡片互盖，尤其 3:4。
- 复查语音触发点与高亮词，开头／中段／结尾及每处接点检查音画同步。长视频不能只验前三秒。
- 自动检查和听感判断分别记录。没有真实原片时只报告合成素材验证，不能声称完成真人口型同步验收。
- 视频之外仍完成三种独立排版海报、发布标题、描述与话题。动画模板或其演示不代替这些交付。

API 依据：[Remotion 渲染接口](https://www.remotion.dev/docs/renderer/render-media)、[动画属性](https://www.remotion.dev/docs/animating-properties)、[视频层](https://www.remotion.dev/docs/offthreadvideo)。

## 平台白色按钮叠层检查

目标为抖音、视频号等带白色操作叠层的平台时，尤其 9:16、3:4 竖屏，按实际目标比例检查。此检查不把平台版本的背景限制扩展到所有横版视频，也不自动替换用户认可的奶白风格。正文、转场和结尾都要检查，不能只验封面。

- 在验收预览中叠加白色点赞、评论、收藏、分享图标和底部白色文字，检查视频本身留白最多、明度最高的帧，以及明暗变化的转场。优先使用实际目标平台的叠层参考；没有参考时可用示意叠层，明确它不代表平台精确布局或已完成发布验收。
- 右侧和底部不仅要留位置，还要让白色图标及细线轮廓在手机尺寸下清楚可见。不要依赖平台可能存在的投影弥补浅底；近白背景、细网格或轻微灰度变化不能作为修复。
- 对比不足时为该平台版本调整相关区域底色，或在平台操作区域后方加足够深的有色渐变；不要靠把重点内容移到白色按钮下方来增加对比。浅色真实界面可保留在内容区。
- 叠层仅用于检查，导出视频不烧录这些仿平台按钮。记录实际检查的时间点与结果；只做模拟检查时，不声称抖音或视频号发布后已验收。
