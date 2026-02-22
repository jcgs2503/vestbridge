"""Agent identity — ID generation, metadata storage, and directory management."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from vestbridge.config import AGENTS_DIR


class AgentMetadata(BaseModel):
    agent_id: str
    name: str = "default"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    mandate: str = "default"


def create_agent(name: str = "default", agents_dir: Path | None = None) -> AgentMetadata:
    """Create a new agent with a unique ID and directory structure."""
    agents_dir = agents_dir or AGENTS_DIR
    agent_id = f"agt_{uuid.uuid4().hex[:8]}"

    agent_dir = agents_dir / agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "keys").mkdir(exist_ok=True)

    metadata = AgentMetadata(agent_id=agent_id, name=name)

    with open(agent_dir / "metadata.yaml", "w") as f:
        yaml.dump(metadata.model_dump(mode="json"), f, default_flow_style=False)

    return metadata


def load_agent(agent_id: str, agents_dir: Path | None = None) -> AgentMetadata:
    """Load agent metadata from its directory."""
    agents_dir = agents_dir or AGENTS_DIR
    metadata_path = agents_dir / agent_id / "metadata.yaml"

    if not metadata_path.exists():
        raise FileNotFoundError(f"Agent not found: {agent_id}")

    with open(metadata_path) as f:
        data = yaml.safe_load(f)

    return AgentMetadata(**data)


def list_agents(agents_dir: Path | None = None) -> list[AgentMetadata]:
    """List all registered agents."""
    agents_dir = agents_dir or AGENTS_DIR
    agents = []

    if not agents_dir.exists():
        return agents

    for agent_dir in sorted(agents_dir.iterdir()):
        if not agent_dir.is_dir():
            continue
        metadata_path = agent_dir / "metadata.yaml"
        if metadata_path.exists():
            with open(metadata_path) as f:
                data = yaml.safe_load(f)
            agents.append(AgentMetadata(**data))

    return agents


def get_or_create_default_agent(agents_dir: Path | None = None) -> AgentMetadata:
    """Get the default agent, creating one if none exist."""
    agents = list_agents(agents_dir)
    if agents:
        return agents[0]
    return create_agent("default", agents_dir)


def get_agent_audit_path(agent_id: str, agents_dir: Path | None = None) -> Path:
    """Get the audit log path for an agent."""
    agents_dir = agents_dir or AGENTS_DIR
    return agents_dir / agent_id / "audit.jsonl"
