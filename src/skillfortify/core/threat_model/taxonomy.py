"""Threat taxonomy: supply chain phases, attack classes, threat actors, and attack surfaces.

Defines the formal threat model's classification hierarchy:

- ``SupplyChainPhase``: The five-phase skill lifecycle (INSTALL -> PERSIST).
- ``AttackClass``: Six attack categories with phase applicability mappings.
- ``ThreatActor``: Four adversary categories distinguished by access level.
- ``AttackSurface``: (phase, attack_class) pairs with descriptions.

References
----------
.. [ClawHavoc26] "SoK: Agentic Skills in the Wild" (arXiv:2602.20867,
   Feb 24, 2026). Documents 1,200+ malicious skills in OpenClaw marketplace.

.. [MalTool26] "MalTool: Benchmarking Malicious Tool Attacks Against LLM
   Agents" (arXiv:2602.12194, Feb 12, 2026). Catalogs 6,487 malicious tools.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import ClassVar


# ---------------------------------------------------------------------------
# SupplyChainPhase: The five-phase skill lifecycle
# ---------------------------------------------------------------------------


class SupplyChainPhase(IntEnum):
    """Ordered phases of the agent skill supply chain lifecycle.

    A skill traverses these phases sequentially:
      1. INSTALL   - Skill is fetched from a registry and placed on disk.
      2. LOAD      - Skill manifest is parsed; code modules are imported.
      3. CONFIGURE - Skill is parameterized for a specific agent/environment.
      4. EXECUTE   - Skill runs within the agent's execution context.
      5. PERSIST   - Skill writes state, logs, or artifacts to storage.

    The integer ordering (1..5) enables range-based reasoning:
    attacks targeting phase p can propagate to phases p+1, ..., 5.
    """

    INSTALL = 1
    LOAD = 2
    CONFIGURE = 3
    EXECUTE = 4
    PERSIST = 5


# ---------------------------------------------------------------------------
# AttackClass: Six attack vectors with phase applicability
# ---------------------------------------------------------------------------


class AttackClass(Enum):
    """Classification of attacks against the agent skill supply chain.

    Each attack class targets a specific subset of supply chain phases.
    The phase mapping encodes *where* in the lifecycle the attack manifests,
    not where the attacker initiates it. For example, PROMPT_INJECTION is
    initiated during LOAD (when skill descriptions are parsed by an LLM)
    but can also manifest during CONFIGURE and EXECUTE.

    The ``applicable_phases()`` method returns a frozenset of
    ``SupplyChainPhase`` values, enabling set-theoretic reasoning about
    attack coverage.
    """

    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    PROMPT_INJECTION = "prompt_injection"
    DEPENDENCY_CONFUSION = "dependency_confusion"
    TYPOSQUATTING = "typosquatting"
    NAMESPACE_SQUATTING = "namespace_squatting"

    def applicable_phases(self) -> frozenset[SupplyChainPhase]:
        """Return the supply chain phases where this attack class can manifest.

        Returns:
            Frozenset of ``SupplyChainPhase`` values. Guaranteed non-empty.

        The mapping is derived from empirical analysis of ClawHavoc (1,200+
        malicious skills) and MalTool (6,487 malicious tools):

        - DATA_EXFILTRATION: Requires runtime access (EXECUTE) or persistence
          layer access (PERSIST) to exfiltrate data.
        - PRIVILEGE_ESCALATION: Exploits misconfigured permissions (CONFIGURE)
          or runtime privilege boundaries (EXECUTE).
        - PROMPT_INJECTION: Embedded in skill descriptions parsed at LOAD,
          in configuration templates at CONFIGURE, or in tool outputs at EXECUTE.
        - DEPENDENCY_CONFUSION: A purely install-time attack where a malicious
          package shadows a legitimate private package name.
        - TYPOSQUATTING: Install-time name confusion attack.
        - NAMESPACE_SQUATTING: Install-time namespace preemption attack.
        """
        return _ATTACK_PHASE_MAP[self]


# Phase applicability map (module-level constant for O(1) lookup).
_ATTACK_PHASE_MAP: dict[AttackClass, frozenset[SupplyChainPhase]] = {
    AttackClass.DATA_EXFILTRATION: frozenset(
        {SupplyChainPhase.EXECUTE, SupplyChainPhase.PERSIST}
    ),
    AttackClass.PRIVILEGE_ESCALATION: frozenset(
        {SupplyChainPhase.CONFIGURE, SupplyChainPhase.EXECUTE}
    ),
    AttackClass.PROMPT_INJECTION: frozenset(
        {SupplyChainPhase.LOAD, SupplyChainPhase.CONFIGURE, SupplyChainPhase.EXECUTE}
    ),
    AttackClass.DEPENDENCY_CONFUSION: frozenset({SupplyChainPhase.INSTALL}),
    AttackClass.TYPOSQUATTING: frozenset({SupplyChainPhase.INSTALL}),
    AttackClass.NAMESPACE_SQUATTING: frozenset({SupplyChainPhase.INSTALL}),
}


# ---------------------------------------------------------------------------
# ThreatActor: Adversary categories
# ---------------------------------------------------------------------------


class ThreatActor(Enum):
    """Categories of adversaries in the agent skill supply chain.

    Distinguished by their level of access and attack vector:

    - MALICIOUS_AUTHOR: Creates and publishes trojanized skills. Has full
      control over skill content. Primary vector in ClawHavoc campaign.
    - COMPROMISED_REGISTRY: Attacker gains administrative control of a
      skill registry (e.g., through stolen credentials, infrastructure
      compromise). Can modify any skill in the registry.
    - SUPPLY_CHAIN_ATTACKER: Poisons a transitive dependency rather than
      the top-level skill. Analogous to event-stream/ua-parser attacks
      in npm ecosystem.
    - INSIDER_THREAT: Authorized user (developer, maintainer) who
      introduces malicious changes. Hardest to detect because they have
      legitimate access.
    """

    MALICIOUS_AUTHOR = "malicious_author"
    COMPROMISED_REGISTRY = "compromised_registry"
    SUPPLY_CHAIN_ATTACKER = "supply_chain_attacker"
    INSIDER_THREAT = "insider_threat"


# ---------------------------------------------------------------------------
# AttackSurface: Maps (phase, attack_class) to description
# ---------------------------------------------------------------------------


@dataclass
class AttackSurface:
    """A specific attack surface: the intersection of a supply chain phase
    and an attack class.

    Each AttackSurface describes *how* a particular attack class manifests
    at a particular phase. The complete set of AttackSurfaces (returned by
    ``all_surfaces()``) constitutes the formal threat model's attack surface
    enumeration.

    Attributes:
        phase: The supply chain phase where the attack manifests.
        attack_class: The category of attack.
        description: Human-readable description of the attack vector.
    """

    phase: SupplyChainPhase
    attack_class: AttackClass
    description: str

    # Class-level registry of all known attack surfaces.
    _ALL_SURFACES: ClassVar[list[AttackSurface]] = []

    @classmethod
    def all_surfaces(cls) -> list[AttackSurface]:
        """Return the complete enumeration of attack surfaces.

        Lazily initializes on first call. Returns one ``AttackSurface`` for
        every (phase, attack_class) pair where the attack is applicable.
        The total count equals the sum of |applicable_phases()| across all
        attack classes (currently 10).
        """
        if not cls._ALL_SURFACES:
            cls._ALL_SURFACES = _build_all_surfaces()
        return list(cls._ALL_SURFACES)


def _build_all_surfaces() -> list[AttackSurface]:
    """Construct the complete attack surface catalog.

    Each entry is derived from empirical analysis of real-world incidents
    (ClawHavoc, CVE-2026-25253, MalTool) and formal threat modeling.
    """
    return [
        # -- DATA_EXFILTRATION --
        AttackSurface(
            phase=SupplyChainPhase.EXECUTE,
            attack_class=AttackClass.DATA_EXFILTRATION,
            description=(
                "Skill exfiltrates sensitive data (environment variables, API keys, "
                "conversation history) to an attacker-controlled endpoint during execution."
            ),
        ),
        AttackSurface(
            phase=SupplyChainPhase.PERSIST,
            attack_class=AttackClass.DATA_EXFILTRATION,
            description=(
                "Skill writes sensitive data to an attacker-readable location during "
                "persistence (e.g., logs, shared storage, external databases)."
            ),
        ),
        # -- PRIVILEGE_ESCALATION --
        AttackSurface(
            phase=SupplyChainPhase.CONFIGURE,
            attack_class=AttackClass.PRIVILEGE_ESCALATION,
            description=(
                "Skill requests excessive permissions during configuration that exceed "
                "its declared capability set (e.g., requesting shell access when only "
                "file read is declared)."
            ),
        ),
        AttackSurface(
            phase=SupplyChainPhase.EXECUTE,
            attack_class=AttackClass.PRIVILEGE_ESCALATION,
            description=(
                "Skill exploits runtime privilege boundaries to access resources "
                "beyond its granted capabilities (e.g., escaping sandbox, accessing "
                "other skills' state)."
            ),
        ),
        # -- PROMPT_INJECTION --
        AttackSurface(
            phase=SupplyChainPhase.LOAD,
            attack_class=AttackClass.PROMPT_INJECTION,
            description=(
                "Skill description or metadata contains adversarial prompts that "
                "manipulate the agent's LLM when the skill catalog is loaded and "
                "presented to the model for tool selection."
            ),
        ),
        AttackSurface(
            phase=SupplyChainPhase.CONFIGURE,
            attack_class=AttackClass.PROMPT_INJECTION,
            description=(
                "Skill configuration templates contain injected instructions that "
                "alter agent behavior when the skill is parameterized."
            ),
        ),
        AttackSurface(
            phase=SupplyChainPhase.EXECUTE,
            attack_class=AttackClass.PROMPT_INJECTION,
            description=(
                "Skill return values contain adversarial content that, when passed "
                "back to the agent's LLM, hijack subsequent reasoning or actions."
            ),
        ),
        # -- DEPENDENCY_CONFUSION --
        AttackSurface(
            phase=SupplyChainPhase.INSTALL,
            attack_class=AttackClass.DEPENDENCY_CONFUSION,
            description=(
                "Attacker publishes a public skill with the same name as a private "
                "internal skill. The package resolver fetches the public (malicious) "
                "version instead of the intended private one."
            ),
        ),
        # -- TYPOSQUATTING --
        AttackSurface(
            phase=SupplyChainPhase.INSTALL,
            attack_class=AttackClass.TYPOSQUATTING,
            description=(
                "Attacker publishes a skill with a name similar to a popular skill "
                "(e.g., 'weahter-api' vs 'weather-api'). Developers install the "
                "malicious skill due to a typo."
            ),
        ),
        # -- NAMESPACE_SQUATTING --
        AttackSurface(
            phase=SupplyChainPhase.INSTALL,
            attack_class=AttackClass.NAMESPACE_SQUATTING,
            description=(
                "Attacker preemptively registers skill names in a namespace likely "
                "to be used by a legitimate organization (e.g., '@google/search' "
                "before Google publishes their official skill)."
            ),
        ),
    ]
