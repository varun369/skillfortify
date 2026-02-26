"""DY-Skill: Dolev-Yao Attacker Model for Agent Skill Supply Chains.

This package formalizes the first adaptation of the Dolev-Yao (DY) network
attacker model to the domain of agentic AI skill supply chains. In the
classical DY model, an attacker controls the communication network between
principals and can intercept, inject, synthesize, decompose, and replay
messages. We map these capabilities onto the agent skill ecosystem:

    Network message   ->  SkillMessage  (skill package flowing through the supply chain)
    Network channel   ->  SupplyChain   (author -> registry -> developer -> environment)
    Protocol run      ->  Skill lifecycle (INSTALL -> LOAD -> CONFIGURE -> EXECUTE -> PERSIST)

Submodules
----------
- ``taxonomy``: SupplyChainPhase, AttackClass, ThreatActor, AttackSurface
- ``messages``: SkillMessage, Registry, SupplyChain
- ``dy_skill``: DYSkillAttacker
"""

from skillfortify.core.threat_model.dy_skill import DYSkillAttacker
from skillfortify.core.threat_model.messages import Registry, SkillMessage, SupplyChain
from skillfortify.core.threat_model.taxonomy import (
    AttackClass,
    AttackSurface,
    SupplyChainPhase,
    ThreatActor,
)

__all__ = [
    "AttackClass",
    "AttackSurface",
    "DYSkillAttacker",
    "Registry",
    "SkillMessage",
    "SupplyChain",
    "SupplyChainPhase",
    "ThreatActor",
]
