"""DY-Skill message types: SkillMessage, Registry, and SupplyChain.

In the DY-Skill model, a ``SkillMessage`` is the analog of a network message
in the classical Dolev-Yao model. It is the atomic unit that the attacker
can intercept, inject, synthesize from, decompose, and replay.

``Registry`` models a skill distribution channel (the untrusted network),
and ``SupplyChain`` models the full topology of authors, registries,
developers, and execution environments.

References
----------
.. [DY83] Dolev, D. & Yao, A. (1983). "On the Security of Public Key
   Protocols." IEEE Transactions on Information Theory, 29(2), 198-208.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# SkillMessage: The atomic unit in the DY-Skill model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillMessage:
    """A skill message flowing through the supply chain.

    In the DY-Skill model, a SkillMessage is the analog of a network message
    in the classical Dolev-Yao model. It is the atomic unit that the attacker
    can intercept, inject, synthesize from, decompose, and replay.

    The ``frozen=True`` constraint ensures immutability: once created, a
    SkillMessage cannot be modified. This is essential for the knowledge set
    semantics -- the attacker's knowledge is a *set* of immutable messages.

    Attributes:
        skill_name: The registered name of the skill (e.g., "weather-api").
        version: Semantic version string (e.g., "1.2.0").
        payload: The raw bytes of the skill's code/configuration.
        capabilities: Frozenset of capability strings the skill declares
            (e.g., {"network:read", "file:write"}). Uses the ``resource:action``
            naming convention from capability-based security.
    """

    skill_name: str
    version: str
    payload: bytes
    capabilities: frozenset[str]


# ---------------------------------------------------------------------------
# Registry: A skill distribution channel
# ---------------------------------------------------------------------------


@dataclass
class Registry:
    """A skill registry (distribution channel) in the supply chain.

    Registries are the primary attack surface for supply chain attacks:
    they are the untrusted channel through which skills flow from authors
    to developers. In the DY model, the registry is analogous to the
    network that the attacker controls.

    Attributes:
        name: Registry identifier (e.g., "official", "community").
        skills: Ordered list of published skill messages.
    """

    name: str
    skills: list[SkillMessage] = field(default_factory=list)

    def publish(self, msg: SkillMessage) -> None:
        """Publish a skill message to this registry.

        In the real world, this corresponds to uploading a skill package
        to a marketplace (OpenClaw, Anthropic Skills, community registries).

        Args:
            msg: The skill message to publish.
        """
        self.skills.append(msg)


# ---------------------------------------------------------------------------
# SupplyChain: The topology of authors, registries, developers, environments
# ---------------------------------------------------------------------------


@dataclass
class SupplyChain:
    """The supply chain topology connecting authors to execution environments.

    Models the complete flow: Author -> Registry -> Developer -> Environment.
    This is the "network" that the DY-Skill attacker controls.

    Attributes:
        authors: Set of skill author identifiers.
        registries: Named registries (the untrusted distribution channels).
        developers: Set of developer identifiers who install skills.
        environments: Set of execution environments where skills run.
    """

    authors: set[str]
    registries: dict[str, Registry]
    developers: set[str]
    environments: set[str]

    @classmethod
    def example(cls) -> SupplyChain:
        """Create an example supply chain for testing and demonstration.

        Returns a realistic topology with:
        - 3 authors (one potentially malicious)
        - 2 registries (official + community)
        - 2 developers
        - 2 environments (staging + production)
        - 2 pre-loaded skills in the official registry

        This mirrors the real-world structure of the OpenClaw/Anthropic
        Skills ecosystem as of February 2026.
        """
        official_registry = Registry(name="official")
        community_registry = Registry(name="community")

        # Pre-load the official registry with legitimate skills.
        official_registry.publish(
            SkillMessage(
                skill_name="web-search",
                version="2.0.0",
                payload=b"def search(query): ...",
                capabilities=frozenset({"network:read"}),
            )
        )
        official_registry.publish(
            SkillMessage(
                skill_name="file-reader",
                version="1.1.0",
                payload=b"def read(path): ...",
                capabilities=frozenset({"file:read"}),
            )
        )

        return cls(
            authors={"alice", "bob", "mallory"},
            registries={
                "official": official_registry,
                "community": community_registry,
            },
            developers={"dev-team-1", "dev-team-2"},
            environments={"staging", "production"},
        )
