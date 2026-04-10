import json
import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 导入业务 workflow
from workflow.conversational_tone_work_flow import app as workflow_app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    source_text: str

@app.post("/api/generate_script_sse")
async def generate_script_sse(req: GenerateRequest):
    async def event_generator():
        initial_state = {
            "oral_content": req.source_text,
            "script": "",
            "loop_details": []
        }
        
        # 记录开始状态
        yield f"data: {json.dumps({'type': 'setup', 'message': 'Workflow Initialized'})}\n\n"
        
        try:
            # 尝试使用 LangGraph 提供的 astream (异步方法)
            # stream_mode="updates" 会给每个产生变化到的节点回流增量更新参数
            async for chunk in workflow_app.astream(initial_state, stream_mode="updates", version="v2"):
                data_str = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {data_str}\n\n"
        except AttributeError:
            # 向后兼容由于版本不同引起的 astream 缺失等问题
            for chunk in workflow_app.stream(initial_state, stream_mode="updates", version="v2"):
                data_str = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {data_str}\n\n"
                await asyncio.sleep(0.01) # 让出协程控制权以防同步 stream 阻塞死循环

        # 结束信号流
        yield f"data: {json.dumps({'type': 'end', 'message': 'Workflow Compeleted'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
