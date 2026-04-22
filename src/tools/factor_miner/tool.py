"""
Factor miner LangChain tools.

Host-side tools that the agent calls to persist factors and manage experience
memory.  ``workspace_id`` is injected from ``RunnableConfig.configurable``,
never passed by the LLM.
"""

import logging
from typing import Any, Dict, List, Tuple, Union

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.tools.factor_miner.implementations import (
    admit_factor_impl,
    get_factor_memory_impl,
    list_factors_impl,
    update_factor_memory_impl,
)

logger = logging.getLogger(__name__)


def _get_workspace_id(config: RunnableConfig) -> str:
    """Extract workspace_id from the runnable config."""
    configurable = config.get("configurable", {})
    workspace_id = configurable.get("workspace_id")
    if not workspace_id:
        raise ValueError("workspace_id not found in config")
    return workspace_id


@tool(response_format="content_and_artifact")
async def admit_factor(
    name: str,
    formula: str,
    ic_mean: float,
    evaluation_config: dict,
    category: str | None = None,
    icir: float | None = None,
    max_corr: float | None = None,
    parameters: dict | None = None,
    config: RunnableConfig = None,
) -> Tuple[str, Dict[str, Any]]:
    """将评估通过的因子存入因子库。

    Args:
        name: 因子名称（如 "F001_momentum_5d"）
        formula: 因子表达式（如 "rank(ts_delta($close, 5))"）
        ic_mean: IC 均值（绝对值）
        evaluation_config: 评估配置（应至少包含以下之一：universe, symbols, start_date, end_date, forward_return_days）
        category: 因子分类（如 "momentum", "volatility"）
        icir: ICIR 值
        max_corr: 与已有因子的最大相关性
        parameters: 可选参数
    """
    workspace_id = _get_workspace_id(config)
    result = await admit_factor_impl(
        workspace_id=workspace_id,
        name=name,
        formula=formula,
        category=category,
        ic_mean=ic_mean,
        icir=icir,
        max_corr=max_corr,
        evaluation_config=evaluation_config,
        parameters=parameters or {},
    )
    return result["message"], result


@tool(response_format="content_and_artifact")
async def list_factors(
    config: RunnableConfig = None,
) -> Tuple[Union[List[Dict[str, Any]], str], Dict[str, Any]]:
    """列出当前工作区的已入库因子。

    Returns:
        因子列表，包含 id, name, formula, category, ic_mean, icir, max_corr, evaluation_config。
    """
    workspace_id = _get_workspace_id(config)
    result = await list_factors_impl(workspace_id)
    count = len(result["factors"])
    content = f"当前工作区共有 {count} 个已入库因子" if count > 0 else "当前工作区还没有入库因子"
    return content, result


@tool(response_format="content_and_artifact")
async def get_factor_memory(
    config: RunnableConfig = None,
) -> Tuple[str, Dict[str, Any]]:
    """读取当前工作区的 Experience Memory。

    如果不存在返回默认空结构。Memory 包含 recommended patterns, forbidden directions, insights 和 recent logs。
    """
    workspace_id = _get_workspace_id(config)
    result = await get_factor_memory_impl(workspace_id)
    rec_count = len(result.get("recommended", []))
    forb_count = len(result.get("forbidden", []))
    content = f"Experience Memory: {rec_count} recommended, {forb_count} forbidden"
    return content, result


@tool(response_format="content_and_artifact")
async def update_factor_memory(
    memory_patch: dict,
    config: RunnableConfig = None,
) -> Tuple[str, Dict[str, Any]]:
    """合并并更新当前工作区的 Experience Memory。

    Args:
        memory_patch: 要合并的记忆内容。可包含:
            - recommended: 推荐模式列表（每条含 pattern, description, example_formula）
            - forbidden: 禁止方向列表（每条含 direction, description, correlated_with）
            - insights: 洞察字符串列表
            - recent_logs: 日志列表（每条含 batch, candidates, passed_ic, passed_corr, admitted）
    """
    workspace_id = _get_workspace_id(config)
    result = await update_factor_memory_impl(workspace_id, memory_patch)
    return result["message"], result
