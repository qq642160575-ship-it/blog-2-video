from typing import TypedDict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import END
from langgraph.graph import StateGraph

from agents.content_reviewer import content_reviewer_agent
from prompts.manager import PromptManager

MAX_LOOPS = 3 # 最多循环 3 次
MIN_SCORE_THRESHOLD = 80 # 评估分数达到 80 结束循环
import os
for k in [
    "ALL_PROXY",
    "all_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
]:
    os.environ.pop(k, None)

class LoopDetails(TypedDict):
    loop_count: int
    current_score: int
    feedback:str


class State(TypedDict):
    oral_content: str
    script: str
    loop_details: List[LoopDetails]

# node1: 内容口语化
def content_writer(state: State, prompt_manager) -> State:
    # 获取创作者的基础系统消息
    writer_messages = prompt_manager.get_langchain_messages(
        'content_writer'
    )
    # 确保 prompt_manager 返回的是一个列表，并且我们可以追加
    if not isinstance(writer_messages, list):
        writer_messages = [writer_messages] # 如果不是列表，转换为列表

    # 总是包含原始口语内容，作为 HumanMessage
    writer_messages.append(HumanMessage(f"原始口语内容：\n{state['oral_content']}"))

    # 如果有历史修改建议，将它们作为历史上下文提供给创作者
    if state.get('loop_details'):
        writer_messages.append(HumanMessage("以下是你之前生成的文案以及评估者给出的历史修改建议："))
        for idx, detail in enumerate(state['loop_details']):
            writer_messages.append(HumanMessage(f"第 {detail['loop_count']} 轮评估反馈：\n{detail['feedback']}"))

        # 最后，给出当前待修改的文案，并明确要求根据历史反馈进行修改
        writer_messages.append(HumanMessage(f"请根据以上历史反馈，修改以下文案：\n{state['script']}"))
    else:
        # 第一次生成，直接要求口语化
        writer_messages.append(HumanMessage(f"请将以上原始口语内容进行口语化：\n{state['oral_content']}"))


    result = content_reviewer_agent['model'].invoke(writer_messages).content

    return {
        'oral_content': state['oral_content'],
        'script': result,
        'loop_details': state['loop_details'], # loop_details 由 content_reviewer 节点更新
    }

# node2: 内容评估： 生成和评估分离
def content_reviewer(state: State, prompt_manager) -> State:
    # 获取评估者的基础系统消息
    reviewer_messages = prompt_manager.get_langchain_messages(
        'content_reviewer'
    )
    if not isinstance(reviewer_messages, list):
        reviewer_messages = [reviewer_messages]

    # 如果有历史评估反馈，将它们作为上下文提供给评估者，以避免重复建议
    if state.get('loop_details'):
        reviewer_messages.append(HumanMessage("以下是你之前给出的修改建议，请在本次评估中避免重复，并基于最新文案给出新的、有价值的反馈："))
        for idx, detail in enumerate(state['loop_details']):
            reviewer_messages.append(HumanMessage(f"第 {detail['loop_count']} 轮反馈：{detail['feedback']}"))


    reviewer_messages.append(HumanMessage(f"请评估以下文案：\n{state['script']}"))
    # 调用模型进行结构化输出评估
    result_structured = content_reviewer_agent['model'].with_structured_output(
        content_reviewer_agent['response_format']
    ).invoke(reviewer_messages)

    # 更新 loop_details
    new_loop_detail = LoopDetails(
        loop_count=len(state.get('loop_details', [])) + 1,
        current_score=result_structured.score,
        feedback=result_structured.feedback
    )
    if 'loop_details' not in state or not state['loop_details']:
        state['loop_details'] = [new_loop_detail]
    else:
        state['loop_details'].append(new_loop_detail)

    return {
        'oral_content': state['oral_content'],
        'script': state['script'], # 评估节点不修改 script
        'loop_details': state['loop_details'],
    }

def should_continue_evaluation(state: State) -> str:
    if not state.get('loop_details'):
        # 这种情况通常不应该发生，除非 content_reviewer 没有正确更新 loop_details
        return "continue_writing"

    latest_detail = state['loop_details'][-1]
    current_score = latest_detail['current_score']
    current_loop_count = latest_detail['loop_count']

    print(f"Current Loop: {current_loop_count}, Score: {current_score}")

    if current_score < MIN_SCORE_THRESHOLD and current_loop_count < MAX_LOOPS:
        return "continue_writing"
    else:
        return "end"

# 1. 构建图
workflow = StateGraph(State)
prompt_manager = PromptManager()
workflow.add_node("content_writer", lambda state: content_writer(state, prompt_manager))
workflow.add_node("content_reviewer", lambda state: content_reviewer(state, prompt_manager))
workflow.set_entry_point("content_writer")
workflow.add_edge("content_writer", "content_reviewer")

workflow.add_conditional_edges(
    "content_reviewer",
    should_continue_evaluation,
    {
        "continue_writing": "content_writer", # 继续写作
        "end": END                             # 结束循环
    }
)
app = workflow.compile()

if __name__ == '__main__':
    initial_state = {
        "oral_content": """
        ## 为什**么模型会有输入长度（上下文）**限制？
    
    1. 训练阶段的位置编码（positional encodeing）
        
        如果没有位置编码，那么transformer就变成了”词袋”：假设输入的是[我，爱，你]， 若没有了位置编码， 那么本质和输入[你， 爱，我]，模型输出的结果应该是一致的。“我爱你”和“你爱我”，在它眼里不过是同一把零件；而人类却知道，这中间隔着的，不只是顺序，而是一整个未曾说出口的结局。
        
        有了位置编码，模型终于学会了“记住顺序”这件事情，同样是「我，爱，你」，它不再只是捧着一袋零散的词语发呆，而是能分清谁先开口，谁在回应，谁站在句子的开头，谁落在结尾。于是，“我爱你”和“你爱我”，不再是同一把零件，而是两种截然不同的命运——一个是奔赴，一个是回响。
        
        可是模型训练的时候，只见过有限长度序列，比如4k-8k，甚至更长，但是终究是有上限的。也就是说，一旦你把句子拉得太长，超过了它熟悉的范围，就会发生两件事：
        
        - 有些模型根本没有为更远的位置定义编码（走到了地图的尽头了）
        - 有些模型即便“强行延伸”（位置插值算法），也会开始失去对位置的精确感知
    2. 部署成本的“物理墙”：KV Cache显存占用
        
        在现实的工业部署中，即便我们解决了位置编码的“地图边界”问题（比如使用 RoPE 旋转位置编码或 ALiBi 这种理论上支持无限长度的方案），**KV Cache 这堵“物理墙”，把长文本的梦想拉回现实。**
        
        如果说模型权重是开发商交付的”清水房“， 那么 KV Cache 就是你搬进去后不断增加的“家具”。
        
        - 模型的权重(Weights)是固定的, 比如Llama-3-8B（8B代表它有80亿参数）永远占用15GB。但是KV Cache是随着对话长度 $L_{seq}$线性增长的
        
        ---
        
        $VRAM_{KVCache} = 2 \times n_{layers} \times n_{heads} \times d_{head} \times L_{seq} \times \text{Bytes\_per\_param}$
        
        以如 Llama-3-8B举例（`n_layers = 32` `n_heads = 32` `d_head = 128` `Bytes = 2(fp16)` )：
        
        - 当你试图处理一个128k的超长文档时，仅KV Cache这一项就会吃掉16GB的显存
        - 即使你手里有一张顶级显卡（如 RTX 4090 24GB），去掉模型权重的 15GB，留给“记忆”的余地只有 9GB。这意味着：**你想让模型读一整本小说，它可能读到一半，显存就因为“公摊面积”太大而直接炸裂（OOM）。**
        
        ---
    
        """,
        "script": "",
        "loop_details": []
    }

    for chunk in app.stream(initial_state, stream_mode="updates", version="v2"):
        print(chunk["type"])  # "updates"
        print(chunk["ns"])    # ()
        print(chunk["data"])  # {"node_name": {"key": "value"}}