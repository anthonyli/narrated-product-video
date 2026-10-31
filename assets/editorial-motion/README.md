# 可复用编辑式视觉布局

`editorial_samples.py` 提供 Pillow 原创图形布局，输出 1920×1080 RGBA。NumPy、Pillow、FFmpeg 是已有依赖；使用同包 shared-motion/transitions.py，不复制第二份特效。两个 JSON 是真实可运行输入，不是仅规划的分镜字段。

```sh
python editorial_samples.py --config api-example.json api.mp4
python editorial_samples.py --config memory-example.json memory.mp4
```

这些入口生成无声视觉样片，`-an` 明确无音轨。不能当成完整配音成片；正式配音和字幕仍用技能既有流程。底部默认标注“无声视觉样片 · 原创图形 / 流程示意”，正式制作必须先完成相应验收，不能只删标识冒称完成。

## 接口

`render_layout(layout, content, t)` 返回图像。`render_config(config, output)` 按总时长编码。配置包含 `width=1920,height=1080,fps=24|30|60,scenes`；每场为 `layout,duration,content,transition`。每场duration含它末尾的转场，下一场在其边界开始。可选transition：`kind=ripple|radial|flip,duration=.15..1,origin=[x,y],axis=x|y,background`。

所有布局共享内容字段：`title_1,title_2,section,kicker,footer_label,background,palette`。palette支持CREAM、INK、ORANGE、BLUE、PAPER、MUT、GREEN、PINK这些语义色角色；某些纸张/网格与深底仍有各布局默认色，精确品牌改造需查看输出。不能说所有颜色已自动适配。

- report_hero：subtitle、number、unit、note、brand、receipt_kicker、receipt_label、receipt_value、receipt_unit、receipt_condition、disclaimer、stamp。
- ledger：subtitle、ledger_title、column_1、column_2、rows（三组二项）、footer、marginal_1、marginal_2。
- process_note：process_title、steps（三组编号/说明）、footer。
- notebook：subtitle、notebook_title、notebook_subtitle、notes（三组标题/说明/底色）、aside_1、aside_2。
- index_detail：index_title、index_rows（三条）、detail_kicker、detail_title、detail_rows（三条）、disclaimer。
- timeline：nodes（三组时点/动作）、equation_left、equation_right。

这些是六种不同视觉模型，不是万能自动美术：数量固定三个的布局会明确拒绝其他数量，长标题必须另行排版，不能无限压字号。用render_layout实际检查关键帧，发现文字越界或模型不适合内容就换布局/扩展实现。不要把任何主题都强塞到本例三场。

示例事实：API金额/路径取2026-10-30已核验的OpenAI规则，真实资格仍以领取页为准；Claude-Mem示例是文档基础上的假设场景，不是运行结果。下一主题不得照搬这些事实或默认品牌名。

## 工程边界与测试

渲染入口拒绝覆盖已存在的输出，发布新版本请换文件名。当前布局固定1080p横版，文本不自动折行；可配置内容不代表任意长度都安全。原布局含有示例默认品牌/事实，换主题要显式覆盖相关字段并查看最终帧。缺字请安装兼容字体或修改font入口，不能静默退成方框。使用系统NotoSansCJK Regular/Bold和DejaVuSans-Bold；字体未附在包内。

同一进程顺序调用；布局参数通过临时绘制上下文传递，不支持多线程并行调用。并行渲染使用独立进程。固定种子的静态纸纹不参与随机抽选风格。无外部图像下载、收费API或参考片素材。

```
python -m unittest discover -s assets/editorial-motion/tests
```

测试实际渲染六种布局、参数校验、确定性、主题色不泄漏、浮点转场边界以及拒绝覆盖。它们验证可运行性，视觉质量仍以实际关键帧和原速片段审阅为准。

可在Python启动前用 `VIDEO_FONT_REGULAR`、`VIDEO_FONT_BOLD`、`VIDEO_FONT_LATIN` 指向有授权的本机字体；文件缺失明确失败，不自动下载、不声称跨平台已验证。换字体后必须重新检查字宽与裁切。

### 示例来源（2026-10-30核验）

API：[OpenAI开发文档](https://developers.openai.com/api/docs/guides/chatgpt-api-credits)、[资格说明](https://help.openai.com/en/articles/20001626-api-credits-benefit-for-eligible-chatgpt-subscriptions)。金额与路径不是永久权益承诺，使用前重新核对官方规则和实际领取页。

记忆示例：[thedotmack/claude-mem README](https://github.com/thedotmack/claude-mem)。登录问题是说明检索步骤的假设场景，没有安装运行项目，不是实测结果。
