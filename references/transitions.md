# 可执行转场 API（v4）

实现：`assets/shared-motion/transitions.py`；依赖 Pillow、NumPy，纯 CPU，不影响原 `core.py`/音频入口。

```python
import sys
sys.path.insert(0, 'PATH/TO/SKILL/assets/shared-motion')
from transitions import transition
frame = transition(before, after, progress,
    kind='ripple', origin=(0.32,0.48), feather=.015,
    strength=.018, rings=3, axis='x', background='#f5f2ea')
```

`before/after` 是同尺寸 PIL Image，返回 RGBA；progress为0..1有限数。端点精确等于输入转换为RGBA的拷贝，中间无随机。参数不合法明确失败，不退成淡入淡出。每帧由调用方把局部时间除以时长得到 progress；不可整片倍速。

| kind | 实际实现 | 语义选择 |
|---|---|---|
| ripple | 圆形揭示+波前局部径向折射+弱波环 | 点击、问题触发、信号传播；origin落在可见触发物 |
| radial | 柔边圆形遮罩从origin扩散到全画幅 | 展开一个结论/放大选中信息；中心不是随机角落 |
| flip | 透视式卡片绕x/y轴转向，半程换正面，文字不镜像 | 翻页、看条件背面、状态对应；不是柔性卷页模拟 |

origin归一化；feather .001–.1、strength 0–.06相对画布短边、rings 1–8。axis只能x/y。推荐转场0.35–0.65秒，阅读阶段保持稳定；超过1秒写明意义。翻转半程会暂时edge-on，只显示底色，这是效果几何，不应该持续黑屏；主体说明必须在前后有足够阅读时间。

不要把 effects 字符串直接塞入旧 Remotion/GSAP scene JSON：这是显式 Python/PIL API。需要旧路线使用时先按帧生成过渡片段或适配其渲染器，不能声称已有原生参数。

## 验证

`python -m unittest discover -s assets/shared-motion/tests`

覆盖精确端点、无源图修改、确定性、透明缝隙、尺寸、语义中心、翻转不镜像、ripple非radial别名、坏参数拒绝。实际视觉仍需原速播放，分别截取before/middle/after；记录是否闪帧、文字撕裂、边缘残留、遮挡或不合内容，不能只看首尾。
