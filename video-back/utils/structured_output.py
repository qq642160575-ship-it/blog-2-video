import asyncio
import json
from typing import Any, Type

from pydantic import BaseModel

from utils.logger import get_logger

logger = get_logger(__name__)


def _extract_text_content(raw_response: Any) -> str:
    content = getattr(raw_response, "content", raw_response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    text_parts.append(str(text))
            else:
                text = getattr(item, "text", None)
                if text:
                    text_parts.append(str(text))
        return "\n".join(text_parts)
    return str(content)


def _extract_json_block(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in model response")
    return text[start : end + 1]


def _normalize_structured_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "__dict__"):
        return vars(value)
    return value


def invoke_structured(
    *,
    model: Any,
    schema: Type[BaseModel],
    messages: list[Any],
    operation: str,
) -> BaseModel:
    methods = ("json_schema", "function_calling")

    for method in methods:
        try:
            logger.info("Structured invoke start operation=%s method=%s", operation, method)
            try:
                runnable = model.with_structured_output(schema, method=method)
            except TypeError:
                runnable = model.with_structured_output(schema)
            result = runnable.invoke(messages)
            normalized = _normalize_structured_value(result)
            validated = result if isinstance(result, schema) else schema.model_validate(normalized)
            logger.info("Structured invoke success operation=%s method=%s", operation, method)
            return validated
        except Exception as e:
            logger.warning("Structured invoke failed operation=%s method=%s error=%s", operation, method, str(e))
            continue

    logger.warning("Falling back to raw JSON parsing operation=%s", operation)
    try:
        raw_response = model.invoke(messages)
        raw_text = _extract_text_content(raw_response)
        json_block = _extract_json_block(raw_text)
        parsed = json.loads(json_block)
        validated = schema.model_validate(parsed)
        logger.info("Structured invoke success operation=%s method=raw_json_fallback", operation)
        return validated
    except Exception as e:
        logger.error("Raw JSON fallback failed operation=%s error=%s", operation, str(e))
        raise ValueError(f"Failed to parse structured output for {operation}: {str(e)}") from e


async def ainvoke_structured(
    *,
    model: Any,
    schema: Type[BaseModel],
    messages: list[Any],
    operation: str,
) -> BaseModel:
    """invoke_structured 的异步版本。

    使用 asyncio.to_thread 将同步的 LLM 调用放入线程池，
    确保 asyncio 事件循环在 LLM 等待期间不被阻塞，
    从而使 SSE/WebSocket 等实时推送能正常工作。
    """
    return await asyncio.to_thread(
        invoke_structured,
        model=model,
        schema=schema,
        messages=messages,
        operation=operation,
    )
