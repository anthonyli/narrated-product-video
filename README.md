# narrated-product-video

把录制视频或主题素材制作成配音视频、动态信息层或共享元素连续动画，并整理独立口播稿、封面及发布文案。

项目地址：[anthonyli/narrated-product-video](https://github.com/anthonyli/narrated-product-video)。这是面向 Agent 的视频制作技能，默认优先使用本地模型生成配音，百炼作为可选云端后端。已知问题见历史[审查记录](docs/review-2026-10-09.md)；这里仍包含原作者的系列视觉偏好，使用者可按自己的品牌要求覆盖。

2026-10-09：Remotion 及配套包已从 4.0.529 升级至 4.0.534，增加依赖锁文件，并通过包含视频、独立音轨、中文字幕与动画的 4 秒合成素材实渲和完整解码检查。迁入清单保留升级前的哈希，作为历史基线。

## 已有能力

- 保留原声：根据 EDL 同步剪辑画面与声音，输出剪辑映射。
- 生成配音：优先当前电脑上的 Qwen3-TTS；Apple Silicon 使用 MLX，Linux 云电脑可用 PyTorch CPU，提供安装与合成说明；另保留可选百炼适配脚本、连续音轨处理和字幕对齐。
- 动态信息层：提供 Remotion 标题、关键词、卡片及字幕模板，保留原录屏制作路线。
- 共享元素连续动画：[制作与节奏规范](references/shared-motion.md)覆盖连续 UI 重排、聚焦、迁移和遮罩，沿用已认可的源码及风格。默认横版 1080p、独立口播稿、不烧录口播字幕；慢节奏通过动作时序与衔接修复，不用全片倍速。
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

## 安装与本地配音

克隆本仓库，将仓库目录作为技能目录交给支持 `SKILL.md` 的 Agent。需要安装到 Codex 时，可将 `SKILL.md`、`agents/`、`references/`、`scripts/` 和 `assets/` 一起复制到自己的技能目录 `narrated-product-video/`；不要只复制入口文件，也不要覆盖已有安装中的个人修改。

```sh
git clone https://github.com/anthonyli/narrated-product-video.git
cd narrated-product-video
```

生成口播前，请按[本地配音安装说明](references/local-tts.md)准备环境：

- 参考方案：Apple Silicon Mac、Python 3.10+、`mlx-audio` 与 `Qwen3-TTS-12Hz-1.7B-Base-4bit`。
- 首次安装需要联网下载依赖和模型；模型与依赖准备完成后可使用本地路径离线推理，不需要百炼账号或 API Key。
- 每位使用者自行提供本人或获授权的声音样本及准确转写；仓库不包含作者音色、模型权重、声音 ID 或密钥。
- Windows／Linux／Intel Mac 不直接照搬 MLX 命令；参考文档提供 Qwen3-TTS 上游入口。环境不满足时不自动切换云端。
- 本地语音合成与字幕识别是两个步骤，当前没有一键完成所有本地后端安装及字幕适配的脚本。

## 运行条件

Python 3、FFmpeg、可用的中文字体；截图渲染需要 Pillow，FFmpeg 也可由 imageio-ffmpeg 提供。动画路径需要 Node.js、npm 和模板 package.json 中固定版本的依赖。首次渲染可能需要下载渲染内核。依赖安装在任务副本中。

详细命令分别位于 [本地配音（默认）](references/local-tts.md)、[录屏流程](references/recorded-video.md)、[动画路线选择](references/motion.md)、[共享元素动画](references/shared-motion.md)、[百炼流程（可选）](references/bailian.md) 和 [截图流程](references/timeline.md)。当前尚无覆盖所有后端的安装自检，也未在干净机器上验证首次运行。

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

当前按技能源码维护，尚未声明稳定发行版；首次运行、完整制作与人工听感验收应分别核实。


## 云端 v3 动画验收补强

详见 [CHANGELOG-v3.md](CHANGELOG-v3.md) 和 [验收门禁](references/acceptance.md)。正式共享元素视频需分别完成分镜、连续短样片和最终配音时间轴检查。主画面低变化扫描只标疑点；验收检查器校验证据及成片哈希，不自动证明审美合格。旧渲染、字幕、配音接口保持不变。

## Editorial v4 增量

阅读 `CHANGELOG-v4.md`、`references/editorial-art-direction.md` 与 `assets/editorial-motion/README.md`。新增可执行六布局及 ripple/radial/flip，不替换旧配音/渲染入口。按 `record.editorial-v4.template.json` 记录真实验收；运行check_acceptance时加 `--require-profile editorial-v4`。脚本合格不等于美学合格，未看的证据不可填通过。
