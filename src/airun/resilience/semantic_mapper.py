"""Semantic Equivalence Mapping Engine.

Translates prompts, system instructions, function/tool schemas, and generation parameters
across AI providers (OpenAI, Anthropic, Google Gemini, Ollama/vLLM) so automated failovers
execute seamlessly without breaking caller applications.

Implements the SPECIFICATION.md requirement:
"Semantic Equivalence Mapping: If Provider A goes down, airun doesn't just switch to
Provider B. It translates the system prompts, adjusts the temperature, and reformats
the tool-calling schemas to ensure Provider B behaves exactly like Provider A."
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def normalize_provider(provider: str) -> str:
    """Normalize provider name strings."""
    p = provider.lower().strip()
    if "anthropic" in p or "claude" in p:
        return "anthropic"
    elif "google" in p or "gemini" in p:
        return "google"
    elif "openai" in p or "gpt" in p:
        return "openai"
    elif "local" in p or "vllm" in p or "ollama" in p or "llama" in p:
        return "local"
    return "openai"


def map_messages(
    messages: List[Dict[str, Any]],
    target_provider: str,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Translates standard message list into target provider dialect.

    Returns:
    (mapped_messages, extracted_system_prompt)
    """
    target = normalize_provider(target_provider)
    system_prompt: Optional[str] = None
    converted_messages: List[Dict[str, Any]] = []

    for msg in messages:
        role = msg.get("role", "user").lower()
        content = msg.get("content", "")

        if role == "system":
            if target == "anthropic":
                # Anthropic separates system prompt into top-level parameter
                system_prompt = (system_prompt + "\n\n" + content) if system_prompt else content
            elif target == "google":
                # Gemini uses system_instruction
                system_prompt = (system_prompt + "\n\n" + content) if system_prompt else content
            else:
                # OpenAI / Local keep system message in list
                converted_messages.append({"role": "system", "content": content})
        elif role in ("user", "human"):
            converted_messages.append({"role": "user", "content": content})
        elif role in ("assistant", "ai", "model"):
            converted_messages.append(
                {"role": "assistant" if target != "google" else "model", "content": content}
            )
        else:
            converted_messages.append(msg)

    return converted_messages, system_prompt


def map_tool_schema(
    tool_spec: Dict[str, Any],
    target_provider: str,
) -> Dict[str, Any]:
    """
    Translates function/tool schemas between OpenAI, Anthropic, and Gemini specs.

    OpenAI Schema:
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "...",
            "parameters": { ... json schema ... }
        }
    }

    Anthropic Schema:
    {
        "name": "get_weather",
        "description": "...",
        "input_schema": { ... json schema ... }
    }

    Gemini Schema:
    {
        "name": "get_weather",
        "description": "...",
        "parameters": { ... json schema ... }
    }
    """
    target = normalize_provider(target_provider)

    # Normalize incoming schema into common intermediate representation
    if "function" in tool_spec and isinstance(tool_spec["function"], dict):
        fn = tool_spec["function"]
        name = fn.get("name", "tool")
        description = fn.get("description", "")
        params = fn.get("parameters", {"type": "object", "properties": {}})
    else:
        name = tool_spec.get("name", "tool")
        description = tool_spec.get("description", "")
        params = (
            tool_spec.get("input_schema")
            or tool_spec.get("parameters")
            or {"type": "object", "properties": {}}
        )

    if target == "anthropic":
        return {
            "name": name,
            "description": description,
            "input_schema": params,
        }
    elif target == "google":
        return {
            "name": name,
            "description": description,
            "parameters": params,
        }
    else:  # openai, local, vllm
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": params,
            },
        }


def map_parameters(
    target_provider: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    top_p: float = 1.0,
) -> Dict[str, Any]:
    """
    Normalizes generation parameters across provider quirks.
    e.g. Anthropic max temperature is 1.0; OpenAI supports 0.0 - 2.0.
    """
    target = normalize_provider(target_provider)

    if target == "anthropic":
        clamped_temp = min(1.0, max(0.0, temperature))
        return {
            "temperature": clamped_temp,
            "max_tokens": max_tokens,
            "top_p": min(1.0, max(0.0, top_p)),
        }
    elif target == "google":
        return {
            "temperature": min(2.0, max(0.0, temperature)),
            "max_output_tokens": max_tokens,
            "top_p": min(1.0, max(0.0, top_p)),
        }
    else:  # openai / local
        return {
            "temperature": min(2.0, max(0.0, temperature)),
            "max_tokens": max_tokens,
            "top_p": min(1.0, max(0.0, top_p)),
        }
