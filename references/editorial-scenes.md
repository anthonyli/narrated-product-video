# 可运行的解说场景接口

用于 [知识解说型 MG 动画](editorial-explainer.md)。先按 [分镜契约](editorial-storyboard.md) 确定每段解释任务，再映射到这里的实现；不要为了使用现成组件而扭曲内容。五种场景是起点，复杂地图、物理过程、任意物体运动等仍需扩展组件并实渲检查。

实现位于 `assets/remotion/src/editorial.jsx`，验证位于 `assets/remotion/editorial-contract.mjs`。当前 `scenes` 仅支持 1920×1080 的 **16:9**；其他比例继续使用原 `overlays` 或另做布局，不能仅改 aspect 后宣称完成。模板内置参考片的微动效——入场回弹缩放、场景体缓慢推近（约 2%）、卡片 ±2–3px 慢速微漂浮，顶栏／页码／进度／字幕固定——制作时不要再叠加额外晃动，动感基线的量测依据见 [editorial-explainer.md](editorial-explainer.md)。

## 外层时间轴

沿用 `aspect`, `fps`, `duration`, `audio`, `captions` 和可选 `fontFile`。`duration` 在正式配音视频中来自最终连续音轨；无声视觉样片可使用明确标记的连续静音，不能声称已验证配音节奏。

加入非空 `scenes` 数组时：

- 各场景按全片秒数 `start`、`end` 排序，从 0 连续覆盖到 `duration`，没有空档或重叠。
- 场景内部的 `at`、`revealAt` 均是**相对该场景起点的秒数**，从 0 开始，小于该场景时长。`captions` 仍使用全片时间。
- `overlays` 可省略或为空；不接受非空 `overlays`、`motions` 及全局 `video`、`image`、`videoBox`、`cardBox` 等旧布局字段，因为它们不在新场景路径渲染。
- 未知场景字段会报错。分镜论点、审查结论等放在独立记录中，不能混进渲染 JSON。
- 素材路径相对时间轴 JSON，使用已放在本地的真实图片。嵌套图片也会复制到渲染临时目录。

## 所有场景的公共字段

必填：`id`（唯一）、`kind`、`start`、`end`、`title`。

可选：`eyebrow`（章节短标签）、`summary`（短解释）、`bg`、`accent`、`sourceLabel`（来源或示意说明）。色彩建议用六位十六进制，留出正文与背景的对比度。来源说明可见，但文件级来源映射仍保留在分镜记录里。不要在这里复制完整旁白。

按参考片基线（见 [editorial-explainer.md](editorial-explainer.md)），**凡使用真实截图的场景必须给出可见来源**：用 `sourceLabel` 或 `eyebrow` 标注“官方示例 · 2026.10.07”“官网截图”等出处；示意界面明确标“示意”。顶部 `eyebrow` 兼作持久来源栏的章节标签（品牌／日期／出处），让每个画面都能回答“这是谁的说法”。

| kind | 内容字段 | 实际画面变化 |
| --- | --- | --- |
| `hero` | `focus`；可选 `lead`；`image` 与 `items` 二选一。items 为 1–3 个 `{label, detail?, at}` | 放大核心概念，补充图片或依次出现的解释项 |
| `compare` | `before`、`after`、`revealAt`（大于 0）。每侧 `{label,title?,text?,image 或 items}`，items 为 1–5 个短字符串 | 先建立前态，再出现后态与连接，支持真实前后截图 |
| `flow` | `nodes`、`edges`；可选 `levels` | 节点按各自时间出现，连线按指定方向绘制 |
| `bars` | `items`、`unit`、`sourceLabel`；可选 `maxValue`、`note` | 每条长度按真实数值与共同尺度增长 |
| `demo` | `states` | 同一内容窗依次呈现不同字段或截图，并可显示高亮和指针 |

### flow

`nodes` 为 2–6 个 `{id,label,detail?,at}`，按 at 排序。`edges` 为 1–15 个 `{from,to,label?,at}`，端点必须引用已有节点，不能自连或重复。

默认每个节点一列。分支图可用 `levels: [["entry"], ["branch-a","branch-b"], ["result"]]` 按列排列；每个节点恰好出现一次，最多 4 列、每列最多 3 个节点。节点和连线都应有解释意义，不能把整段旁白切成方框。连线可先于目标节点出现。

### bars

`items` 为 1–5 个 `{label,value,displayValue?,at,color?}`。value 是有限非负数，至少一个值大于零。`maxValue` 为共同轴上限，至少等于最大值；省略时取最大值。浅色轨道表示该上限，色条按比例填充。

`displayValue` 只改可见标注，不改几何值；作者必须核对二者一致。例如 `value: 0.5, displayValue: "1 / 2", maxValue: 1`。当前不支持负值、堆叠、误差棒或断轴；不得伪装已实现。需要数据来源；示例数据要标成示意。审查会提醒核对来源，但不能自动证明数值或引用真实。

### demo

`states` 为 2–5 个按 at 严格递增的状态，第一项 `at: 0`。每项包括 `label`、可选 `title`，以及 `image` 或 `fields` 二选一。

fields 为 1–5 个 `{label,value,changed?}`，value 为字符串。changed 为布尔值，突出当前变化。字段模式是**示意界面**，不证明任何真实软件已经实现功能。

每项还可带：

- `highlights: [{box: [x,y,width,height], label?}]`，1–6 项，归一化坐标，矩形须完全在 0–1 内容区内。
- `pointer: {x,y,label?}`，同样是 0–1 坐标。

坐标相对浏览器标题栏下方的整个内容窗，包括图片 contain 后可能存在的留白，**不是原图像素坐标**。必须看实际渲染再定位。highlight 只圈注、pointer 只提示；状态文件或字段值应真实改变，不能靠移动指针冒充操作。

## 示例与检查

仓库提供 `assets/remotion/examples/meeting.json` 与 `fractions.json`，分别使用任务状态变化与数学数量关系。示例文案不是新主题的填空模板；它们仅用于运行机制与视觉回归。

下面命令假设已按 [motion.md](motion.md) 把工程复制到 `work/task/remotion` 并装好锁定依赖：

```sh
# 生成两份明确标成“无声视觉样片”的配置和连续静音；拒绝覆盖。
node work/task/remotion/examples/prepare.mjs work/task/previews

# 检查结构、时间和本地素材，输出启发式风险报告。
node work/task/remotion/render.mjs work/task/previews/meeting/motion.json outputs/meeting-preview.mp4 --audit-only

# 导出关键变化及稳定帧；目录必须是新目录，不生成 MP4。
node work/task/remotion/render.mjs work/task/previews/meeting/motion.json outputs/meeting-preview.mp4 --stills work/task/stills-meeting

# 实渲；输出名必须尚不存在。
node work/task/remotion/render.mjs work/task/previews/meeting/motion.json outputs/meeting-preview.mp4
```

`--audit-only` 在结构或素材失败时返回非零状态；成功报告 `qualityAssessed: false`。警告包括长时间缺少变化、重复构图/素材、文字比较、示意界面和数据来源等。逐项结合实际内容处理；合理的稳定阅读或数学比较无需为了消除警告而添加动作。

`--stills` 同时生成 `manifest.json`，记录帧号、场景和选择原因。检查这些图还不能代替连续运动检查。正式制作继续完成字幕、音频、完整解码和内容验收，不把无声样例当成完整交付。

自动契约回归可运行 `node --test assets/remotion/tests/editorial-contract.test.mjs`。它验证实现边界，不评判审美。
