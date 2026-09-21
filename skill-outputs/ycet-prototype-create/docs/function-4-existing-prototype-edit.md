# 功能四：现有原型或图片接管

读取 shared-prototype-standards.md 和 shared-change-policy.md。适用于本 Skill 原型、普通 HTML 以及整页图片，不专门维护旧多文件项目链路。

1. 只读分析源 HTML 及关联资源或图片，提取页面、流程和变更。当前端口明确则沿用，仅缺失或冲突时询问，不要求每次重新确认。
2. HTML 首次接管直接整理 prototype/docs/Spec.md 并确认，不调用外部需求访谈 Skill；已有明确需求只补缺口。
3. 普通修改沿用 UI；整体风格调整／重设计进入功能二确认。图片承载保留原图视觉。
4. 已有标准原型普通修改直接沿用元数据类型和 UI，按 shared-change-policy.md 修改，不重新询问 A/B/C。首次接管或类型转换进入功能三；已有明确选型沿用，缺失才询问，不先生成静态中间原型。根据选型和修改范围执行文件策略。
5. 源文件位于 outputs 外时不覆盖来源；标准产物写 outputs。已有标准原型按所选策略修改。

## 图片承载

原图保存 prototype/assets/images/ 并以 data URI 内嵌。每图对应一个 data-ycet-page-id 容器，标记 data-ycet-image-prototype="true"。不 OCR、元素化或以 HTML/CSS 重画图片中的产品元素。

保持比例，完整展示，长图内部滚动。仅当用户明确要求固定区且已确认原图边界，才无损分割固定顶部／中部滚动／固定底部，保留原图与片段。不得猜边界、拉伸或自动裁掉系统 UI；图片与设备壳冲突时先确认处理。

B/C 可以叠加 button.ycet-image-hotspot，设置 aria-label 和 data-ycet-nav-target。默认透明，hover/focus-visible 使用半透明虚线 outline。滚动区热区跟随图片，固定区热区处于对应局部容器。不遮挡未覆盖区域的滚动。A 不绑定业务跨页热区。

制作时保持资源内联、图片比例、固定边界与交互目标有效；完成说明列出来源和限制，不写 EditLog。首次生成目标原型文件保留首次交付验收，包含页面、核心交互及图片／热区等相关检查，遵循 prototype-validation.md；已交付目标原型的后续修改保存后直接结束，不追加验收。

接管旧 mobile 文件或转为 nonframe 时保留来源，重新处理固定宽高、根裁切及滚动容器。新文件基名按类型决定。首次从来源 HTML／图片建立目标交付文件，使用 --mode create --purpose initial 并保留验收；已交付目标原型的后续转换或新增迭代仍属修改，确需调用构建器传 --purpose modify，不因新文件名自动验收。
