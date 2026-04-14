# LLM 增强功能快速开始指南

## 什么是 LLM 增强？

LLM 增强功能使用大语言模型（LLM）替代硬编码规则，让视频生成更智能、更有创意、更个性化。

## 核心改进

### 之前（纯规则）
- ❌ 只有 4 个预设主题配色
- ❌ 风格选择基于简单统计
- ❌ 文本提取用正则表达式
- ❌ 布局只有 10 个固定模板

### 现在（LLM 增强）
- ✅ 无限定制配色，自动适配品牌色
- ✅ 智能理解脚本情感和受众
- ✅ 语义理解，准确提取关键信息
- ✅ 创意布局设计，不局限模板

## 快速使用

### 1. 启用 LLM 增强（推荐）

```python
from orchestration.workflow_runner import WorkflowRunner

runner = WorkflowRunner(
    artifact_service=artifact_service,
    artifact_repo=artifact_repo,
    event_publisher=event_publisher,
    enable_llm_enhancement=True,  # 启用 LLM 增强
    llm_confidence_threshold=0.7,  # 置信度阈值
)

# 运行工作流
result = await runner.run_animation(context, script)
```

### 2. 使用预设配置

```python
from config.llm_enhancement_config import BALANCED_CONFIG

runner = WorkflowRunner(
    artifact_service=artifact_service,
    artifact_repo=artifact_repo,
    event_publisher=event_publisher,
    enable_llm_enhancement=BALANCED_CONFIG.is_enabled,
    llm_confidence_threshold=BALANCED_CONFIG.confidence_threshold,
)
```

### 3. 禁用 LLM 增强（纯规则）

```python
runner = WorkflowRunner(
    artifact_service=artifact_service,
    artifact_repo=artifact_repo,
    event_publisher=event_publisher,
    enable_llm_enhancement=False,  # 禁用 LLM
)
```

## 配置选项

### 平衡模式（推荐）
```python
from config.llm_enhancement_config import BALANCED_CONFIG
```
- LLM 和规则平衡
- 置信度阈值：0.7
- 适合大多数场景

### 保守模式
```python
from config.llm_enhancement_config import CONSERVATIVE_CONFIG
```
- 仅在高置信度时使用 LLM
- 置信度阈值：0.85
- 主题和布局使用规则
- 适合对稳定性要求高的场景

### 激进模式
```python
from config.llm_enhancement_config import AGGRESSIVE_CONFIG
```
- 最大化 LLM 使用
- 置信度阈值：0.5
- 适合追求创意的场景

### 禁用模式
```python
from config.llm_enhancement_config import DISABLED_CONFIG
```
- 完全禁用 LLM
- 使用纯规则
- 适合测试和对比

## 自定义配置

```python
from config.llm_enhancement_config import LLMEnhancementConfig

custom_config = LLMEnhancementConfig(
    mode="hybrid",  # "disabled", "hybrid", "full"
    confidence_threshold=0.75,
    enable_style_analysis=True,      # 风格分析
    enable_theme_generation=True,    # 主题生成
    enable_semantic_extraction=True, # 语义提取
    enable_layout_design=False,      # 布局设计（禁用）
)

runner = WorkflowRunner(
    artifact_service=artifact_service,
    artifact_repo=artifact_repo,
    event_publisher=event_publisher,
    enable_llm_enhancement=custom_config.is_enabled,
    llm_confidence_threshold=custom_config.confidence_threshold,
)
```

## 运行测试

```bash
# 测试所有 LLM 增强功能
python3 -m pytest tests/test_llm_enhancement.py -v

# 测试单个组件
python3 -m pytest tests/test_llm_enhancement.py::test_semantic_intent_extractor -v
python3 -m pytest tests/test_llm_enhancement.py::test_theme_generator -v
python3 -m pytest tests/test_llm_enhancement.py::test_style_analyzer -v
python3 -m pytest tests/test_llm_enhancement.py::test_layout_designer -v

# 测试完整流程
python3 -m pytest tests/test_llm_enhancement.py::test_workflow_runner_with_llm_enhancement -v
```

## 查看结果

生成的 artifact 会包含 LLM 增强的元数据：

```python
# 获取 visual_strategy artifact
visual_artifact = await artifact_repo.get_artifact(visual_artifact_id)

# 查看 LLM 元数据
llm_metadata = visual_artifact.content["llm_metadata"]
print(f"风格来源: {llm_metadata['style_source']}")  # "llm" 或 "rules"
print(f"主题来源: {llm_metadata['theme_source']}")  # "llm" 或 "preset"

# 如果使用了 LLM，可以查看推荐信息
if "llm_recommendation" in llm_metadata:
    recommendation = llm_metadata["llm_recommendation"]
    print(f"推荐风格: {recommendation['style_family']}")
    print(f"置信度: {recommendation['confidence']}")
    print(f"理由: {recommendation['reasoning']}")
```

## 性能考虑

### LLM 调用次数
- 风格分析：1 次（全局）
- 主题生成：1 次（全局）
- 语义提取：N 次（每个场景）
- 布局设计：N 次（每个场景）

**总计**：2 + 2N 次（N = 场景数）

### 示例（5 个场景）
- LLM 调用：12 次
- 预估时间：~24 秒（假设每次 2 秒）

### 优化建议
- 使用缓存减少重复调用
- 根据场景复杂度选择性启用
- 对简单场景禁用布局设计

## 常见问题

### Q: LLM 增强会影响现有功能吗？
A: 不会。LLM 增强是可选的，禁用后完全使用原有规则。

### Q: LLM 调用失败怎么办？
A: 所有 LLM agent 都有 fallback 机制，失败时自动回退到规则。

### Q: 如何控制成本？
A: 使用保守模式，或者只启用部分 LLM 组件（如语义提取和风格分析）。

### Q: 如何提升生成质量？
A: 使用激进模式，或者调低置信度阈值（如 0.5）。

### Q: 如何对比 LLM vs 规则的效果？
A: 运行两次工作流，一次启用 LLM，一次禁用，对比生成结果。

## 更多信息

详细文档请参考：
- `LLM_ENHANCEMENT_SUMMARY.md` - 完整总结
- `generation/llm_agents/` - LLM agent 实现
- `config/llm_enhancement_config.py` - 配置选项
- `tests/test_llm_enhancement.py` - 测试用例

## 反馈和建议

如有问题或建议，请提交 issue 或联系开发团队。
