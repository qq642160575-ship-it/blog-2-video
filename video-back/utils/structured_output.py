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
        except Exception:
            logger.exception("Structured invoke failed operation=%s method=%s", operation, method)

    logger.warning("Falling back to raw JSON parsing operation=%s", operation)
    raw_response = model.invoke(messages)
    raw_text = _extract_text_content(raw_response)
    json_block = _extract_json_block(raw_text)
    parsed = json.loads(json_block)
    validated = schema.model_validate(parsed)
    logger.info("Structured invoke success operation=%s method=raw_json_fallback", operation)
    return validated
