# narrated-product-video

把录制视频或主题素材制作成带配音、字幕和动态信息层的视频，并整理封面及发布文案。

当前状态：**本地审查基线，尚未发布**。仓库保留了现有技能的 15 个源文件，以便逐项核对改动；已知问题见 [审查记录](docs/review-2026-10-09.md)。这里仍包含原作者的系列视觉偏好，尚未完成通用化。

2026-10-09：Remotion 及配套包已从 4.0.529 升级至 4.0.534，增加依赖锁文件，并通过包含视频、独立音轨、中文字幕与动画的 4 秒合成素材实渲和完整解码检查。迁入清单保留升级前的哈希，作为历史基线。

## 已有能力

- 保留原声：根据 EDL 同步剪辑画面与声音，输出剪辑映射。
- 生成配音：提供百炼适配脚本、连续音轨处理和字幕对齐。
- 动态信息层：提供 Remotion 标题、关键词、卡片及字幕模板。
- 简单截图视频：提供 FFmpeg/Pillow 渲染路径。
- 视觉分类：全屏实录演示、鲜明宣传，以及[知识解说型 MG 动画](references/editorial-explainer.md)（浅色信息图／纸感拼贴）。解说路径先做论点、证据和可见状态分镜，再映射到实际画面。
- 横版解说场景：新增 `hero`、`compare`、`flow`、`bars`、`demo`，包含比例图、连线、真实图片或示意字段的多状态演示。新 `scenes` 接口当前仅支持 16:9，原 `overlays` 接口保留。
- 制作检查：`--audit-only` 检查参数与素材并提示表达风险；`--stills` 导出关键状态。两者均不自动判定审美质量。[接口与可运行示例](references/editorial-scenes.md)包含无声视觉样片的生成命令。

这些工具需要 Agent 根据真实素材编排。当前不承诺只输入主题即可无人干预完成制作，也不承诺传播效果。

## 仓库结构

- `SKILL.md`：任务路由与制作规则。
- `references/`：录屏、配音、动画及传播表达说明。
- `scripts/`：Python 处理脚本。
- `assets/remotion/`：复制到任务目录使用的动画工程。
- `agents/openai.yaml`：技能入口元数据。
- `docs/baseline-manifest.json`：本次迁入源文件的 SHA-256 清单。

## 运行条件

Python 3、FFmpeg、可用的中文字体；截图渲染需要 Pillow，FFmpeg 也可由 imageio-ffmpeg 提供。动画路径需要 Node.js、npm 和模板 package.json 中固定版本的依赖。首次渲染可能需要下载渲染内核。依赖安装在任务副本中。

详细命令分别位于 [录屏流程](references/recorded-video.md)、[动画流程](references/motion.md)、[百炼流程](references/bailian.md) 和 [截图流程](references/timeline.md)。当前尚无覆盖所有后端的安装自检，也未在干净机器上验证首次运行。

## 私有数据与产物

所有项目数据使用项目内相对路径，命令从项目根目录执行；技能安装目录只提供规则和模板。

- `private/voice/voice-preferences.json`：声音偏好，内部素材路径相对该配置文件所在目录。
- `private/voice/`：声音样本、已有授权声音响应（如 `bailian-voice.json`）。
- `private/models/`：本地语音模型；声音配置中的模型路径相对配置所在目录解析。
- `private/fonts/`：由用户提供、具备使用权限的字体；通过时间轴相对引用。
- `work/<task>/`：当次原始素材、服务响应和中间文件。
- `outputs/`：交付产物。
- `archive/YYYY-MM-DD/<topic>/`：按实际制作日期整理的历史视频、全部版本、素材和工程；本地索引见 `archive/INDEX.md`。

`private/`、`work/`、`outputs/`、`archive/` 已被 Git 忽略。换电脑时，项目私有数据需随项目单独安全迁移，Git 克隆不会带上它们。历史归档保留当时的运行环境和脚本，旧位置的兼容链接用于维持本机已有引用，不等同于跨机器环境已验证。凭据由执行环境提供，例如 `DASHSCOPE_API_KEY`；不把密钥写入可提交文件或声音偏好配置。不会自动读取个人主目录或历史项目里的配置。

`.gitignore` 只是辅助措施，发布前仍需检查实际提交内容。当前审查扫描通过不等于对任意未来新增文件的保证。

## 许可与发布状态

本项目自己的许可证尚未选定。依赖不随项目代码自动变更许可；使用 Remotion 前查看其 [许可说明](https://www.remotion.dev/docs/license/faq)。素材、字体和声音参考也需具备相应使用权限。

当前仅初始化了本地 Git 仓库，没有提交、配置远程、创建 GitHub 仓库或推送。当前已知问题和定位讨论完成后再形成首个发布版本。
