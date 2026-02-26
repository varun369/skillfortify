"""Tests for threat taxonomy: SupplyChainPhase, AttackClass, ThreatActor, AttackSurface.

Validates the formal threat model's classification hierarchy including
phase ordering, attack-phase mappings, threat actor enumeration, and
attack surface coverage completeness.
"""

from __future__ import annotations

from skillfortify.core.threat_model import (
    AttackClass,
    AttackSurface,
    SupplyChainPhase,
    ThreatActor,
)


# ---------------------------------------------------------------------------
# SupplyChainPhase
# ---------------------------------------------------------------------------


class TestSupplyChainPhase:
    """Validate the five-phase supply chain lifecycle."""

    def test_all_five_phases_exist(self) -> None:
        phases = list(SupplyChainPhase)
        assert len(phases) == 5

    def test_phases_are_ordered(self) -> None:
        """Phases must monotonically increase: INSTALL < LOAD < ... < PERSIST."""
        assert SupplyChainPhase.INSTALL.value < SupplyChainPhase.LOAD.value
        assert SupplyChainPhase.LOAD.value < SupplyChainPhase.CONFIGURE.value
        assert SupplyChainPhase.CONFIGURE.value < SupplyChainPhase.EXECUTE.value
        assert SupplyChainPhase.EXECUTE.value < SupplyChainPhase.PERSIST.value

    def test_install_is_first(self) -> None:
        assert SupplyChainPhase.INSTALL.value == 1

    def test_persist_is_last(self) -> None:
        assert SupplyChainPhase.PERSIST.value == 5

    def test_phase_names(self) -> None:
        expected = {"INSTALL", "LOAD", "CONFIGURE", "EXECUTE", "PERSIST"}
        actual = {p.name for p in SupplyChainPhase}
        assert actual == expected


# ---------------------------------------------------------------------------
# AttackClass
# ---------------------------------------------------------------------------


class TestAttackClass:
    """Validate the six attack classes and their phase applicability."""

    def test_six_attack_classes_exist(self) -> None:
        classes = list(AttackClass)
        assert len(classes) == 6

    def test_attack_class_names(self) -> None:
        expected = {
            "DATA_EXFILTRATION",
            "PRIVILEGE_ESCALATION",
            "PROMPT_INJECTION",
            "DEPENDENCY_CONFUSION",
            "TYPOSQUATTING",
            "NAMESPACE_SQUATTING",
        }
        actual = {a.name for a in AttackClass}
        assert actual == expected

    def test_each_attack_has_phases(self) -> None:
        """Every attack class must target at least one supply chain phase."""
        for attack in AttackClass:
            phases = attack.applicable_phases()
            assert len(phases) > 0, f"{attack.name} has no applicable phases"

    def test_applicable_phases_return_type(self) -> None:
        """applicable_phases() must return a frozenset of SupplyChainPhase."""
        for attack in AttackClass:
            phases = attack.applicable_phases()
            assert isinstance(phases, frozenset)
            for phase in phases:
                assert isinstance(phase, SupplyChainPhase)

    def test_data_exfiltration_phases(self) -> None:
        phases = AttackClass.DATA_EXFILTRATION.applicable_phases()
        assert phases == frozenset({SupplyChainPhase.EXECUTE, SupplyChainPhase.PERSIST})

    def test_privilege_escalation_phases(self) -> None:
        phases = AttackClass.PRIVILEGE_ESCALATION.applicable_phases()
        assert phases == frozenset({SupplyChainPhase.CONFIGURE, SupplyChainPhase.EXECUTE})

    def test_prompt_injection_phases(self) -> None:
        phases = AttackClass.PROMPT_INJECTION.applicable_phases()
        assert phases == frozenset(
            {SupplyChainPhase.LOAD, SupplyChainPhase.CONFIGURE, SupplyChainPhase.EXECUTE}
        )

    def test_dependency_confusion_phases(self) -> None:
        phases = AttackClass.DEPENDENCY_CONFUSION.applicable_phases()
        assert phases == frozenset({SupplyChainPhase.INSTALL})

    def test_typosquatting_phases(self) -> None:
        phases = AttackClass.TYPOSQUATTING.applicable_phases()
        assert phases == frozenset({SupplyChainPhase.INSTALL})

    def test_namespace_squatting_phases(self) -> None:
        phases = AttackClass.NAMESPACE_SQUATTING.applicable_phases()
        assert phases == frozenset({SupplyChainPhase.INSTALL})

    def test_install_phase_attacks(self) -> None:
        """Three attack classes target the INSTALL phase."""
        install_attacks = [
            a for a in AttackClass if SupplyChainPhase.INSTALL in a.applicable_phases()
        ]
        assert len(install_attacks) == 3

    def test_execute_phase_attacks(self) -> None:
        """Three attack classes target the EXECUTE phase."""
        execute_attacks = [
            a for a in AttackClass if SupplyChainPhase.EXECUTE in a.applicable_phases()
        ]
        assert len(execute_attacks) == 3


# ---------------------------------------------------------------------------
# ThreatActor
# ---------------------------------------------------------------------------


class TestThreatActor:
    """Validate the four threat actor categories."""

    def test_four_actors_exist(self) -> None:
        actors = list(ThreatActor)
        assert len(actors) == 4

    def test_actor_names(self) -> None:
        expected = {
            "MALICIOUS_AUTHOR",
            "COMPROMISED_REGISTRY",
            "SUPPLY_CHAIN_ATTACKER",
            "INSIDER_THREAT",
        }
        actual = {a.name for a in ThreatActor}
        assert actual == expected


# ---------------------------------------------------------------------------
# AttackSurface
# ---------------------------------------------------------------------------


class TestAttackSurface:
    """Validate attack surface mappings."""

    def test_attack_surface_creation(self) -> None:
        surface = AttackSurface(
            phase=SupplyChainPhase.INSTALL,
            attack_class=AttackClass.TYPOSQUATTING,
            description="Attacker publishes skill with similar name to popular skill.",
        )
        assert surface.phase == SupplyChainPhase.INSTALL
        assert surface.attack_class == AttackClass.TYPOSQUATTING
        assert "similar name" in surface.description

    def test_attack_surface_requires_valid_phase(self) -> None:
        """The attack_class must be applicable to the given phase."""
        surface = AttackSurface(
            phase=SupplyChainPhase.INSTALL,
            attack_class=AttackClass.TYPOSQUATTING,
            description="Valid combination.",
        )
        assert surface.phase in surface.attack_class.applicable_phases()

    def test_attack_surface_equality(self) -> None:
        s1 = AttackSurface(
            phase=SupplyChainPhase.EXECUTE,
            attack_class=AttackClass.DATA_EXFILTRATION,
            description="Skill sends data to external endpoint.",
        )
        s2 = AttackSurface(
            phase=SupplyChainPhase.EXECUTE,
            attack_class=AttackClass.DATA_EXFILTRATION,
            description="Skill sends data to external endpoint.",
        )
        assert s1 == s2

    def test_attack_surface_coverage(self) -> None:
        """Every (phase, attack_class) pair where the attack is applicable
        must have a corresponding AttackSurface description.

        This ensures no attack vector is left undocumented in the model.
        """
        surfaces = AttackSurface.all_surfaces()
        surface_pairs = {(s.phase, s.attack_class) for s in surfaces}

        for attack_class in AttackClass:
            for phase in attack_class.applicable_phases():
                assert (phase, attack_class) in surface_pairs, (
                    f"Missing AttackSurface for ({phase.name}, {attack_class.name})"
                )

    def test_attack_surface_total_count(self) -> None:
        """The total number of surfaces equals the sum of applicable phases across attacks.

        DATA_EXFILTRATION: 2, PRIVILEGE_ESCALATION: 2, PROMPT_INJECTION: 3,
        DEPENDENCY_CONFUSION: 1, TYPOSQUATTING: 1, NAMESPACE_SQUATTING: 1
        Total: 10
        """
        surfaces = AttackSurface.all_surfaces()
        assert len(surfaces) == 10
