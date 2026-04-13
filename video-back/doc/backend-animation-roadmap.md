# 后端动画生成待办路线

## 1. 文档目的

这份文档只保留后续真正需要推进的后端工作项，作为动画生成后端的执行清单。

使用原则：

- 只写还没完成、接下来要做的事
- 不记录已经完成的事项
- 每个任务尽量能落到代码层
- 优先按短期、中期、长期三个层次推进


## 2. 当前后端后续工作的主线

后续动画后端优化按下面三层推进：

1. 短期优化
2. 中期增强
3. 长期演进

当前优先处理短期优化项。


## 3. 短期优化

短期目标：把当前链路从“能稳定跑”继续推进到“更容易维护、更容易扩展、生成结果更稳”。

### 3.1 增强脚本解析器

目标：

- 提高口播稿切分稳定性
- 为 scene planner 提供更可靠输入

需要做的事：

- 支持中英文标点混合切句
- 支持按段落优先切分
- 支持超长句二次拆分
- 增加无标点输入兜底策略
- 优化 `role` 推断逻辑，避免只靠句子位置判断
- 补齐对应单元测试和边界测试

涉及模块：

- `compiler/parser.py`
- `tests/test_refactor.py`


### 3.2 增强 scene planner

目标：

- 让 scene 规划不只依赖简单角色映射
- 让后续布局和动效编译有更清晰输入

需要做的事：

- 扩展 scene plan 字段，补充更明确的导演层信息
- 增加每个 scene 的信息密度定义
- 增加更合理的视觉目标和镜头类型
- 增加推荐时长或节奏等级
- 优化不同类型文本的场景拆分策略
- 补齐对应测试

涉及模块：

- `compiler/scene_planner.py`
- `compiler/schemas.py`
- `workflow/animation_work_flow.py`
- `tests/test_refactor.py`


### 3.3 规范动画状态结构

目标：

- 继续把动画状态收敛到 scene 维度
- 为后续增量编译、回滚和差异比较打基础

需要做的事：

- 继续围绕 `scene_artifacts` 收口状态读写
- 减少 workflow 和 service 中对平铺字段的直接依赖
- 评估何时移除 `layouts / motions / dsl / codes / validations` 的兼容层
- 明确 `scene_artifacts` 的标准结构定义
- 增加状态结构测试

涉及模块：

- `workflow/animation_work_flow.py`
- `services/scene_service.py`
- `services/workflow_service.py`
- `compiler/schemas.py`


### 3.4 修复编码和进度文案问题

目标：

- 解决日志和 SSE 中的乱码问题
- 保证开发和联调可读性

需要做的事：

- 统一源码文件编码为 UTF-8
- 清理 workflow 和 service 中的乱码字符串
- 统一动画流程中的进度提示文案
- 检查前端是否依赖现有字段和文案格式

涉及模块：

- `services/workflow_service.py`
- `workflow/conversational_tone_work_flow.py`
- `workflow/animation_work_flow.py`
- 其他存在乱码的 Python 文件


### 3.5 完善动画链路测试

目标：

- 降低后续重构风险
- 为持续迭代提供回归保障

需要做的事：

- 增加 parser 复杂输入测试
- 增加 scene planner 多类型输入测试
- 增加 scene_artifacts 结构测试
- 增加 scene 重编译测试
- 增加 patch 后重编译测试
- 增加 workflow 状态恢复测试
- 增加失败场景与 repair 分支测试

涉及模块：

- `tests/test_refactor.py`
- `tests/test_checkpoint_persistence.py`
- 新增更细分的测试文件


## 4. 中期增强

中期目标：提升动画结果质量，让生成结果不再只是规则模板的拼接。

### 4.1 升级布局编译

需要做的事：

- 从固定坐标布局逐步升级到约束式布局
- 支持根据文本长度动态调整盒子尺寸
- 支持不同模板族
- 增加基础碰撞检测
- 增加移动端安全区内的自适应计算

涉及模块：

- `compiler/layout_compiler.py`
- `compiler/schemas.py`
- `compiler/validator.py`


### 4.2 升级动效编译

需要做的事：

- 增加入场、强调、退场分层
- 更好地对齐 marks 节奏
- 为不同 scene 类型定义不同动效策略
- 增加基础转场约束
- 增加动效时间冲突校验

涉及模块：

- `compiler/motion_compiler.py`
- `compiler/marks_engine.py`
- `compiler/validator.py`


### 4.3 建立主题系统

需要做的事：

- 明确定义 `theme_profile` 结构
- 引入颜色、字体、圆角、阴影等基础 token
- 让 layout / code generator 使用主题配置
- 支持至少 2 到 3 种基础主题

涉及模块：

- `workflow/animation_work_flow.py`
- `compiler/code_generator.py`
- `compiler/layout_compiler.py`
- `compiler/schemas.py`


### 4.4 升级 validator 和 repair

需要做的事：

- 增加文本溢出检查
- 增加布局层级冲突检查
- 增加动效引用和时序检查
- 增加代码结构完整性检查
- 扩展 repair 能力，不只修 safe area 越界

涉及模块：

- `compiler/validator.py`
- `compiler/repair.py`
- `compiler/schemas.py`


## 5. 长期演进

长期目标：把后端从“动画编译器”推进为“完整视频生成后端”。

### 5.1 接入渲染链路

需要做的事：

- 增加 composition 组装能力
- 接入 Remotion 实际渲染入口
- 输出可管理的视频文件结果
- 增加渲染日志和失败重试机制


### 5.2 接入音频与字幕

需要做的事：

- 接入 TTS
- 生成字幕切分结果
- 做字幕与时间轴对齐
- 增加音画同步能力


### 5.3 接入素材系统

需要做的事：

- 支持图片、图标、视频素材引用
- 设计素材输入接口
- 增加素材缓存策略
- 预留版权与来源管理能力


### 5.4 引入任务系统

需要做的事：

- 设计渲染任务队列
- 支持任务取消、恢复、重试
- 支持多任务并发控制
- 增加任务级日志和状态追踪


## 6. 推荐执行顺序

建议按下面顺序继续推进：

1. 增强脚本解析器
2. 增强 scene planner
3. 继续规范 scene_artifacts 状态结构
4. 修复编码和进度文案问题
5. 完善测试覆盖
6. 升级布局和动效编译
7. 建立主题系统
8. 升级 validator 和 repair
9. 接入渲染、音频、字幕和任务系统


## 7. 下一步建议

下一步建议直接开始：

1. `parser.py` 增强
2. `scene_planner.py` 增强

这两项会直接影响后续动画生成质量，也是当前短期优化里收益最高的部分。
