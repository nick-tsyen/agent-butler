from __future__ import annotations

import logging

from .registry import get_all_agents, register_agent

logger = logging.getLogger(__name__)


def _load_built_in_agents() -> None:
    try:
        from .built_in import explore, general_purpose

        for module in (explore, general_purpose):
            if hasattr(module, "AGENT_DEFINITION"):
                register_agent(module.AGENT_DEFINITION)
    except ImportError:
        logger.debug("No built-in agents found, skipping.")


async def _load_user_agents() -> None:
    try:
        from ..utils.paths import get_agent_butler_path
        from .load_agents_dir import load_agents_from_dir

        user_agents_dir = get_agent_butler_path("agents")
        definitions = await load_agents_from_dir(user_agents_dir)
        for defn in definitions:
            register_agent(defn)
    except Exception as e:
        logger.debug(f"Failed to load user agents: {e}")


async def bootstrap_agents() -> None:
    _load_built_in_agents()
    await _load_user_agents()
    agents = get_all_agents()
    logger.info(f"Bootstrapped {len(agents)} agent(s): {[a.agent_type for a in agents]}")
