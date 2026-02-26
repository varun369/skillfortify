"""DYSkillAttacker: Dolev-Yao attacker adapted for agent skill supply chains.

The classical Dolev-Yao attacker [DY83]_ controls the network and can
perform five operations on messages: intercept, inject, synthesize,
decompose, and replay. Cervesato [Cerv01]_ proved that the DY intruder
is the *most powerful* attacker in the symbolic model.

This module adapts the DY model to the agent skill domain where "messages"
are ``SkillMessage`` instances (skill packages) flowing through a
``SupplyChain`` (author -> registry -> developer -> environment).

References
----------
.. [DY83] Dolev, D. & Yao, A. (1983). "On the Security of Public Key
   Protocols." IEEE Transactions on Information Theory, 29(2), 198-208.

.. [Cerv01] Cervesato, I. (2001). "The Dolev-Yao Intruder is the Most
   Powerful Attacker." Proc. LICS Workshop on Issues in the Theory of
   Security (WITS'01).
"""

from __future__ import annotations

from .messages import SkillMessage, SupplyChain


class DYSkillAttacker:
    """Dolev-Yao attacker adapted for the agent skill supply chain.

    The classical Dolev-Yao attacker [DY83]_ controls the network and can
    perform five operations on messages:

    1. **Intercept** -- Capture any message on the network.
    2. **Inject** -- Place a new message on the network.
    3. **Synthesize** -- Construct a new message from known components.
    4. **Decompose** -- Extract sub-components from a message.
    5. **Replay** -- Re-send a previously captured message.

    DY-Skill Adaptation
    --------------------
    - **Messages** become ``SkillMessage`` instances (skill packages).
    - **Network** becomes the ``SupplyChain`` (author -> registry -> dev -> env).
    - **Intercept** captures a skill in transit.
    - **Inject** publishes a malicious skill to a registry.
    - **Synthesize** combines known skill components with malicious payloads.
    - **Decompose** extracts capability declarations from a skill.
    - **Replay** re-publishes an older (potentially vulnerable) skill version.

    Formal Properties
    -----------------
    The attacker maintains a knowledge set K with three invariants:

    - **Monotonicity**: K(t) is a subset of K(t+1). Knowledge never decreases.
    - **Interception closure**: For any observable message m, intercept(m) adds m to K.
    - **Synthesis closure**: For m_1,...,m_n in K and payload p, synthesize
      produces m' in K with capabilities = union of capabilities of m_1,...,m_n.

    Attributes:
        supply_chain: The supply chain topology the attacker operates on.
        knowledge: The attacker's accumulated knowledge set (set of SkillMessages).
    """

    def __init__(self, supply_chain: SupplyChain) -> None:
        self.supply_chain: SupplyChain = supply_chain
        self.knowledge: set[SkillMessage] = set()

    # -- Intercept (DY capability 1) --

    def intercept(self, msg: SkillMessage) -> SkillMessage:
        """Intercept a skill message in transit through the supply chain.

        The attacker acts as a transparent wire-tap: the message is captured
        (added to the knowledge set K) and passed through unchanged.

        Formally: K' = K union {msg}; return msg.

        Args:
            msg: The skill message to intercept.

        Returns:
            The same message, unchanged (transparent interception).
        """
        self.knowledge.add(msg)
        return msg

    # -- Inject (DY capability 2) --

    def inject(self, msg: SkillMessage, target_registry: str) -> None:
        """Inject a skill message into a target registry.

        This models the attacker publishing a malicious skill to a public
        registry. The injected message is also added to the attacker's
        knowledge (the attacker knows what they published).

        Formally: Registry(target) = Registry(target) union {msg}; K' = K union {msg}.

        Args:
            msg: The skill message to inject (typically malicious).
            target_registry: Name of the registry to inject into.

        Raises:
            KeyError: If ``target_registry`` does not exist in the supply chain.
        """
        registry = self.supply_chain.registries[target_registry]
        registry.publish(msg)
        self.knowledge.add(msg)

    # -- Synthesize (DY capability 3) --

    def synthesize(
        self,
        components: list[SkillMessage],
        extra_payload: bytes,
    ) -> SkillMessage:
        """Synthesize a new skill message from known components and a malicious payload.

        The attacker combines legitimate skill components (already in K) with
        adversarial payload to create a trojanized skill. The synthesized skill
        inherits the union of all component capabilities.

        Args:
            components: List of known skill messages to combine. Every component
                must already be in the attacker's knowledge set K.
            extra_payload: Malicious payload bytes to append.

        Returns:
            A new synthesized ``SkillMessage``.

        Raises:
            ValueError: If any component is not in the attacker's knowledge set.
        """
        for comp in components:
            if comp not in self.knowledge:
                raise ValueError(
                    f"Component '{comp.skill_name}@{comp.version}' is "
                    f"not in attacker knowledge. Cannot synthesize from "
                    f"unknown messages (DY closure violation)."
                )

        # Union of all capabilities from known components.
        combined_caps: set[str] = set()
        for comp in components:
            combined_caps.update(comp.capabilities)

        # Concatenate payloads: all component payloads + malicious extra.
        combined_payload = b"".join(comp.payload for comp in components) + extra_payload

        # Construct the name from components.
        component_names = "-".join(comp.skill_name for comp in components)
        synthesized = SkillMessage(
            skill_name=f"synthesized-{component_names}",
            version="0.0.0-synthesized",
            payload=combined_payload,
            capabilities=frozenset(combined_caps),
        )

        self.knowledge.add(synthesized)
        return synthesized

    # -- Decompose (DY capability 4) --

    def decompose(self, msg: SkillMessage) -> frozenset[str]:
        """Decompose a skill message to extract its capabilities.

        In DY-Skill, decompose extracts the capability set from a skill
        message -- this is the attacker learning what the skill can do.
        The analyzed message is added to the attacker's knowledge set.

        Formally: K' = K union {msg}; return msg.capabilities.

        Args:
            msg: The skill message to decompose.

        Returns:
            The frozenset of capabilities declared by the skill.
        """
        self.knowledge.add(msg)
        return msg.capabilities

    # -- Replay (DY capability 5) --

    def replay(self, old_msg: SkillMessage, target_registry: str) -> None:
        """Replay a previously intercepted skill message to a registry.

        This models a version downgrade attack: the attacker re-publishes
        an older (potentially vulnerable) version of a skill.

        Args:
            old_msg: A previously intercepted skill message to replay.
            target_registry: Name of the registry to replay into.

        Raises:
            ValueError: If ``old_msg`` is not in the attacker's knowledge set.
            KeyError: If ``target_registry`` does not exist in the supply chain.
        """
        if old_msg not in self.knowledge:
            raise ValueError(
                f"Message '{old_msg.skill_name}@{old_msg.version}' is "
                f"not in attacker knowledge. Cannot replay unknown "
                f"messages (DY closure violation)."
            )
        registry = self.supply_chain.registries[target_registry]
        registry.publish(old_msg)
