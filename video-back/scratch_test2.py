from workflow.compiler_flow import compiler_work_flow
from models.compiler_state import CompilerState
from services.workflow_service import build_animation_initial_state

workflow = compiler_work_flow()
state = build_animation_initial_state("这个是一个测试口播文案。这是第二句测试。")
print("Compiling...")
result = workflow.invoke(state, {"configurable": {"thread_id": "test_123"}})
print(result["last_action"])
