import pytest
from pydantic import BaseModel

from app.mcp.registry import SideEffect, ToolDefinition, ToolRegistry


class ToolInput(BaseModel):
    query: str


class ToolOutput(BaseModel):
    result: str


async def handler(value: ToolInput) -> ToolOutput:
    return ToolOutput(result=value.query.upper())


@pytest.mark.asyncio
async def test_registry_enforces_role_and_schema() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition("knowledge.search", "Search knowledge", frozenset({"analyst"}), SideEffect.read, ToolInput, ToolOutput, 10),
        handler,
    )
    assert (await registry.call("knowledge.search", "analyst", {"query": "stock"})).result == "STOCK"
    with pytest.raises(PermissionError):
        await registry.call("knowledge.search", "viewer", {"query": "stock"})
