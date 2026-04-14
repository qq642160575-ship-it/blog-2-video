"""DeepSeek Chat Model - 兼容 LangChain 的 DeepSeek API 包装器"""

import os
from typing import Any, List, Optional

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class DeepSeekChat(BaseChatModel):
    """DeepSeek Chat Model - 使用 Anthropic 兼容 API"""

    model: str = Field(default="deepseek-chat")
    api_key: str = Field(default="")
    base_url: str = Field(default="https://api.deepseek.com/anthropic")
    temperature: float = Field(default=0.3)
    max_tokens: int = Field(default=81920)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 清除代理环境变量
        for key in ['ALL_PROXY', 'all_proxy', 'HTTP_PROXY', 'http_proxy',
                    'HTTPS_PROXY', 'https_proxy', 'SOCKS_PROXY', 'socks_proxy']:
            os.environ.pop(key, None)

    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        """转换 LangChain 消息格式为 Anthropic 格式"""
        converted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                converted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                converted.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                # Anthropic API 不支持 system 消息，转换为 user 消息
                converted.append({"role": "user", "content": f"[System]: {msg.content}"})
            else:
                converted.append({"role": "user", "content": str(msg.content)})
        return converted

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """生成响应"""
        converted_messages = self._convert_messages(messages)

        # 构建请求
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": converted_messages,
        }

        if stop:
            payload["stop_sequences"] = stop

        # 发送请求
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                },
                json=payload,
                timeout=60.0,
            )

            if response.status_code != 200:
                raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")

            result = response.json()

        # 提取响应内容
        content = ""
        if "content" in result and len(result["content"]) > 0:
            content = result["content"][0].get("text", "")

        # 构建 LangChain 响应
        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)

        return ChatResult(generations=[generation])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """异步生成响应"""
        converted_messages = self._convert_messages(messages)

        # 构建请求
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": converted_messages,
        }

        if stop:
            payload["stop_sequences"] = stop

        # 发送异步请求
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                },
                json=payload,
                timeout=60.0,
            )

            if response.status_code != 200:
                raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")

            result = response.json()

        # 提取响应内容
        content = ""
        if "content" in result and len(result["content"]) > 0:
            content = result["content"][0].get("text", "")

        # 构建 LangChain 响应
        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)

        return ChatResult(generations=[generation])

    @property
    def _llm_type(self) -> str:
        """返回 LLM 类型"""
        return "deepseek-chat"

    @property
    def _identifying_params(self) -> dict:
        """返回识别参数"""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
