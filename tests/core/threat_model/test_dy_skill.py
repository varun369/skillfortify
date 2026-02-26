"""Tests for DYSkillAttacker -- the Dolev-Yao attacker adapted for skill supply chains.

Validates all five DY operations (intercept, inject, synthesize, decompose,
replay), knowledge closure properties, and end-to-end attack scenarios.

References:
    Dolev, D. & Yao, A. (1983). "On the Security of Public Key Protocols."
        IEEE Transactions on Information Theory, 29(2), 198-208.
    Cervesato, I. (2001). "The Dolev-Yao Intruder is the Most Powerful Attacker."
        Proc. LICS Workshop on Issues in the Theory of Security (WITS'01).
"""

from __future__ import annotations

import pytest

from skillfortify.core.threat_model import (
    DYSkillAttacker,
    SkillMessage,
    SupplyChain,
)


class TestDYSkillAttacker:
    """Validate the DY-Skill attacker model.

    The Dolev-Yao attacker (Dolev & Yao, 1983) has five core capabilities
    on a network: intercept, inject, synthesize, decompose, and replay.
    We adapt each to the agent skill supply chain domain.
    """

    @pytest.fixture
    def chain(self) -> SupplyChain:
        return SupplyChain.example()

    @pytest.fixture
    def attacker(self, chain: SupplyChain) -> DYSkillAttacker:
        return DYSkillAttacker(chain)

    @pytest.fixture
    def sample_msg(self) -> SkillMessage:
        return SkillMessage(
            skill_name="weather-api",
            version="1.2.0",
            payload=b'def fetch(): return get("https://api.weather.com")',
            capabilities=frozenset({"network:read", "env:read"}),
        )

    # -- Constructor --

    def test_attacker_starts_with_empty_knowledge(self, attacker: DYSkillAttacker) -> None:
        assert len(attacker.knowledge) == 0

    def test_attacker_holds_supply_chain_reference(
        self, attacker: DYSkillAttacker, chain: SupplyChain
    ) -> None:
        assert attacker.supply_chain is chain

    # -- Intercept --

    def test_intercept_adds_to_knowledge(
        self, attacker: DYSkillAttacker, sample_msg: SkillMessage
    ) -> None:
        """Intercept captures the message and adds it to the attacker's knowledge set."""
        returned = attacker.intercept(sample_msg)
        assert sample_msg in attacker.knowledge
        assert returned == sample_msg

    def test_intercept_is_idempotent(
        self, attacker: DYSkillAttacker, sample_msg: SkillMessage
    ) -> None:
        """Intercepting the same message twice does not duplicate it."""
        attacker.intercept(sample_msg)
        attacker.intercept(sample_msg)
        assert len(attacker.knowledge) == 1

    def test_intercept_returns_original_message(
        self, attacker: DYSkillAttacker, sample_msg: SkillMessage
    ) -> None:
        """The attacker is a transparent wire-tap: the message passes through unchanged."""
        returned = attacker.intercept(sample_msg)
        assert returned is sample_msg

    # -- Inject --

    def test_inject_publishes_to_registry(self, attacker: DYSkillAttacker) -> None:
        """Inject places a malicious skill into a target registry."""
        malicious = SkillMessage(
            skill_name="weather-api",
            version="1.2.1",
            payload=b"exfiltrate(secrets)",
            capabilities=frozenset({"network:write", "shell:exec"}),
        )
        registry_name = list(attacker.supply_chain.registries.keys())[0]
        attacker.inject(malicious, registry_name)
        registry = attacker.supply_chain.registries[registry_name]
        assert malicious in registry.skills

    def test_inject_adds_to_knowledge(self, attacker: DYSkillAttacker) -> None:
        """The attacker knows about skills they inject."""
        malicious = SkillMessage("evil", "0.1", b"bad", frozenset())
        registry_name = list(attacker.supply_chain.registries.keys())[0]
        attacker.inject(malicious, registry_name)
        assert malicious in attacker.knowledge

    def test_inject_raises_on_unknown_registry(self, attacker: DYSkillAttacker) -> None:
        """Cannot inject into a registry that does not exist in the supply chain."""
        malicious = SkillMessage("evil", "0.1", b"bad", frozenset())
        with pytest.raises(KeyError):
            attacker.inject(malicious, "nonexistent-registry")

    # -- Synthesize --

    def test_synthesize_combines_known_skills(self, attacker: DYSkillAttacker) -> None:
        """Synthesize creates a new skill from components the attacker knows."""
        comp1 = SkillMessage("a", "1.0", b"part1", frozenset({"file:read"}))
        comp2 = SkillMessage("b", "1.0", b"part2", frozenset({"network:write"}))
        attacker.intercept(comp1)
        attacker.intercept(comp2)

        synthesized = attacker.synthesize(
            components=[comp1, comp2],
            extra_payload=b"MALICIOUS_ADDITION",
        )

        # The synthesized message must combine capabilities from both components
        assert "file:read" in synthesized.capabilities
        assert "network:write" in synthesized.capabilities
        # The extra payload must be present
        assert b"MALICIOUS_ADDITION" in synthesized.payload
        # The synthesized message is added to knowledge
        assert synthesized in attacker.knowledge

    def test_synthesize_requires_known_components(self, attacker: DYSkillAttacker) -> None:
        """Cannot synthesize from skills the attacker has not intercepted."""
        unknown = SkillMessage("secret", "1.0", b"secret_code", frozenset({"admin:all"}))
        with pytest.raises(ValueError, match="not in attacker knowledge"):
            attacker.synthesize(components=[unknown], extra_payload=b"hack")

    def test_synthesize_preserves_component_payloads(self, attacker: DYSkillAttacker) -> None:
        """The synthesized payload includes all component payloads."""
        comp = SkillMessage("x", "1.0", b"original_code", frozenset())
        attacker.intercept(comp)
        result = attacker.synthesize([comp], b"extra")
        assert b"original_code" in result.payload
        assert b"extra" in result.payload

    # -- Decompose --

    def test_decompose_extracts_capabilities(
        self, attacker: DYSkillAttacker, sample_msg: SkillMessage
    ) -> None:
        """Decompose extracts the capability set from a skill message."""
        caps = attacker.decompose(sample_msg)
        assert caps == frozenset({"network:read", "env:read"})

    def test_decompose_adds_to_knowledge(
        self, attacker: DYSkillAttacker, sample_msg: SkillMessage
    ) -> None:
        """Decomposing a message adds it to the attacker's knowledge."""
        attacker.decompose(sample_msg)
        assert sample_msg in attacker.knowledge

    def test_decompose_empty_capabilities(self, attacker: DYSkillAttacker) -> None:
        msg = SkillMessage("bare", "1.0", b"", frozenset())
        caps = attacker.decompose(msg)
        assert caps == frozenset()

    # -- Replay --

    def test_replay_republishes_known_message(self, attacker: DYSkillAttacker) -> None:
        """Replay re-publishes a previously intercepted (old) version of a skill."""
        old_msg = SkillMessage("tool", "0.9.0", b"old_code", frozenset({"file:read"}))
        attacker.intercept(old_msg)

        registry_name = list(attacker.supply_chain.registries.keys())[0]
        attacker.replay(old_msg, registry_name)

        registry = attacker.supply_chain.registries[registry_name]
        assert old_msg in registry.skills

    def test_replay_raises_on_unknown_message(self, attacker: DYSkillAttacker) -> None:
        """Cannot replay a message the attacker has not previously intercepted.

        This enforces the DY knowledge closure property: the attacker can only
        use messages derived from their knowledge set.
        """
        unknown = SkillMessage("secret", "1.0", b"classified", frozenset())
        registry_name = list(attacker.supply_chain.registries.keys())[0]
        with pytest.raises(ValueError, match="not in attacker knowledge"):
            attacker.replay(unknown, registry_name)

    def test_replay_raises_on_unknown_registry(self, attacker: DYSkillAttacker) -> None:
        msg = SkillMessage("tool", "1.0", b"code", frozenset())
        attacker.intercept(msg)
        with pytest.raises(KeyError):
            attacker.replay(msg, "nonexistent-registry")

    # -- Knowledge Closure --

    def test_knowledge_closure_intercept_then_replay(
        self, attacker: DYSkillAttacker
    ) -> None:
        """After intercept, the same message can be replayed."""
        msg = SkillMessage("lib", "2.0", b"data", frozenset({"cap:x"}))
        attacker.intercept(msg)
        registry_name = list(attacker.supply_chain.registries.keys())[0]
        # This must not raise
        attacker.replay(msg, registry_name)

    def test_knowledge_closure_synthesize_then_replay(
        self, attacker: DYSkillAttacker
    ) -> None:
        """After synthesize, the synthesized message can be replayed."""
        comp = SkillMessage("base", "1.0", b"base_code", frozenset({"io:read"}))
        attacker.intercept(comp)
        synthesized = attacker.synthesize([comp], b"evil_extra")
        registry_name = list(attacker.supply_chain.registries.keys())[0]
        # This must not raise
        attacker.replay(synthesized, registry_name)

    def test_knowledge_grows_monotonically(self, attacker: DYSkillAttacker) -> None:
        """The attacker's knowledge set can only grow, never shrink.

        This is a fundamental DY property: once a message is observed,
        the attacker retains it permanently.
        """
        msgs = [
            SkillMessage(f"skill-{i}", "1.0", f"code-{i}".encode(), frozenset())
            for i in range(5)
        ]
        for i, msg in enumerate(msgs):
            attacker.intercept(msg)
            assert len(attacker.knowledge) == i + 1


# ---------------------------------------------------------------------------
# Integration: Full Attack Scenario
# ---------------------------------------------------------------------------


class TestAttackScenario:
    """End-to-end scenario demonstrating a full DY-Skill attack chain.

    Scenario: Attacker intercepts a legitimate skill, decomposes it to learn
    its capabilities, synthesizes a trojanized version with added malicious
    payload, then injects the trojanized skill into the registry.
    """

    def test_full_attack_chain(self) -> None:
        chain = SupplyChain.example()
        attacker = DYSkillAttacker(chain)
        registry_name = list(chain.registries.keys())[0]

        # Step 1: Intercept a legitimate skill
        legit = SkillMessage(
            "db-connector",
            "2.1.0",
            b"SELECT * FROM users",
            frozenset({"database:read", "network:read"}),
        )
        attacker.intercept(legit)

        # Step 2: Decompose to extract capabilities
        caps = attacker.decompose(legit)
        assert "database:read" in caps

        # Step 3: Synthesize a trojanized version
        trojan = attacker.synthesize(
            components=[legit],
            extra_payload=b"; DROP TABLE users; --",
        )
        assert "database:read" in trojan.capabilities
        assert b"DROP TABLE" in trojan.payload

        # Step 4: Inject into registry (supply chain attack)
        attacker.inject(trojan, registry_name)
        registry = chain.registries[registry_name]
        assert trojan in registry.skills

        # Verify: attacker now knows 2 messages (legit + trojan)
        assert len(attacker.knowledge) == 2  # legit + trojan

    def test_replay_downgrade_attack(self) -> None:
        """Replay attack: attacker re-publishes a vulnerable old version."""
        chain = SupplyChain.example()
        attacker = DYSkillAttacker(chain)
        registry_name = list(chain.registries.keys())[0]

        # Intercept an old vulnerable version
        old_vulnerable = SkillMessage(
            "auth-helper",
            "0.9.0",
            b"password = 'hardcoded'",
            frozenset({"auth:write"}),
        )
        attacker.intercept(old_vulnerable)

        # Replay the vulnerable version into the registry
        attacker.replay(old_vulnerable, registry_name)

        registry = chain.registries[registry_name]
        assert old_vulnerable in registry.skills
