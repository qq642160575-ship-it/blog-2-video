from typing import TypedDict

from agents.coder import CoderResult
from agents.director import DirectorResult
from agents.visual_architect import VisualProtocol


class State(TypedDict):
    script: str  # 脚本
    director: DirectorResult  # 导演分镜内容
    visual_architect: VisualProtocol # 视觉设计内容
    coder: CoderResult # coder生成内容


