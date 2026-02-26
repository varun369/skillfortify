"""Tests for DY-Skill message types: SkillMessage, Registry, SupplyChain.

Validates the core data structures used as the atomic units in the
Dolev-Yao attacker model adapted for agent skill supply chains.
"""

from __future__ import annotations

import pytest

from skillfortify.core.threat_model import (
    Registry,
    SkillMessage,
    SupplyChain,
)


# ---------------------------------------------------------------------------
# SkillMessage
# ---------------------------------------------------------------------------


class TestSkillMessage:
    """Validate skill messages -- the atomic unit in the DY-Skill model."""

    def test_skill_message_creation(self) -> None:
        msg = SkillMessage(
            skill_name="weather-fetch",
            version="1.0.0",
            payload=b"print('hello')",
            capabilities=frozenset({"network:read", "file:none"}),
        )
        assert msg.skill_name == "weather-fetch"
        assert msg.version == "1.0.0"
        assert msg.payload == b"print('hello')"
        assert "network:read" in msg.capabilities

    def test_skill_message_is_frozen(self) -> None:
        """SkillMessage must be immutable (frozen dataclass)."""
        msg = SkillMessage(
            skill_name="test",
            version="0.1.0",
            payload=b"",
            capabilities=frozenset(),
        )
        with pytest.raises(AttributeError):
            msg.skill_name = "mutated"  # type: ignore[misc]

    def test_skill_message_is_hashable(self) -> None:
        """SkillMessage must be usable in sets (attacker knowledge set)."""
        msg = SkillMessage(
            skill_name="test",
            version="0.1.0",
            payload=b"",
            capabilities=frozenset(),
        )
        s = {msg}
        assert msg in s

    def test_skill_message_equality(self) -> None:
        msg1 = SkillMessage("a", "1.0", b"x", frozenset({"cap:a"}))
        msg2 = SkillMessage("a", "1.0", b"x", frozenset({"cap:a"}))
        assert msg1 == msg2

    def test_skill_message_inequality(self) -> None:
        msg1 = SkillMessage("a", "1.0", b"x", frozenset({"cap:a"}))
        msg2 = SkillMessage("a", "2.0", b"x", frozenset({"cap:a"}))
        assert msg1 != msg2


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    """Validate skill registries."""

    def test_registry_creation(self) -> None:
        reg = Registry(name="official")
        assert reg.name == "official"
        assert len(reg.skills) == 0

    def test_registry_publish(self) -> None:
        reg = Registry(name="community")
        msg = SkillMessage("tool", "1.0.0", b"code", frozenset({"file:read"}))
        reg.publish(msg)
        assert len(reg.skills) == 1
        assert reg.skills[0] == msg

    def test_registry_publish_multiple(self) -> None:
        reg = Registry(name="test-reg")
        msg1 = SkillMessage("a", "1.0", b"", frozenset())
        msg2 = SkillMessage("b", "1.0", b"", frozenset())
        reg.publish(msg1)
        reg.publish(msg2)
        assert len(reg.skills) == 2


# ---------------------------------------------------------------------------
# SupplyChain
# ---------------------------------------------------------------------------


class TestSupplyChain:
    """Validate the supply chain topology."""

    def test_supply_chain_creation(self) -> None:
        chain = SupplyChain(
            authors={"alice", "bob"},
            registries={"official": Registry(name="official")},
            developers={"dev1"},
            environments={"staging"},
        )
        assert "alice" in chain.authors
        assert "official" in chain.registries
        assert "dev1" in chain.developers
        assert "staging" in chain.environments

    def test_example_classmethod(self) -> None:
        """example() must return a fully populated SupplyChain."""
        chain = SupplyChain.example()
        assert len(chain.authors) > 0
        assert len(chain.registries) > 0
        assert len(chain.developers) > 0
        assert len(chain.environments) > 0

    def test_example_has_preloaded_skills(self) -> None:
        """The example chain should have at least one skill in a registry."""
        chain = SupplyChain.example()
        total_skills = sum(len(r.skills) for r in chain.registries.values())
        assert total_skills > 0
