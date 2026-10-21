"""Tenant identity and the authorization seam.

A `Principal` is *who is acting*: the tenant they act within, their subject
identifier, and the capabilities they hold. It is deliberately small — the point
is not to be an auth system, but to give every later phase a seam where identity
can be carried instead of assumed.

Why this exists: reviewer identity used to be a self-attested free-text string
typed into a form (`close_keeper/demo_app.py` even labels it "your name
(self-attested)"), and no store knew which tenant it belonged to. Two
consequences followed. A rule could be written into one tenant's store naming a
record from another tenant, and there was no way to ask a database "what does
this customer have on file?" — which is the question a retention, deletion, or
export policy is made of.

`Principal` fixes both without pretending to be more than it is:

* **Tenant binding** — `MemoryStore` and `DecisionLedger` are opened for one
  tenant. Reopening a file under a different tenant raises `TenantMismatch`
  rather than silently serving another customer's rows. A write whose record
  names a different tenant raises `CrossTenantWrite`.
* **Capabilities** — a `Principal` carries roles. `require()` raises
  `PermissionDenied` when an operation needs a role the principal does not
  hold. The local, single-operator implementation
  (`local_principal()`) holds every role, so nothing about the demo changes.

The honest limit, stated here because it belongs next to the code: this is a
*seam*, not an authentication system. `local_principal()` trusts whoever runs
the process. Real deployments replace the principal's construction with a
verified identity; the operations below do not change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from memory_policy import required_text

# Roles. A reviewer decides cells and teaches the memory; an approver also
# governs rules (validate / activate / revoke); an auditor only reads.
ROLE_REVIEWER = "reviewer"
ROLE_APPROVER = "approver"
ROLE_AUDITOR = "auditor"
ROLE_ADMIN = "admin"

ALL_ROLES = frozenset({ROLE_REVIEWER, ROLE_APPROVER, ROLE_AUDITOR, ROLE_ADMIN})

# Every capability a principal can hold, mapped to the role that grants it.
CAPABILITIES = {
    "read": frozenset({ROLE_REVIEWER, ROLE_APPROVER, ROLE_AUDITOR, ROLE_ADMIN}),
    "decide": frozenset({ROLE_REVIEWER, ROLE_APPROVER, ROLE_ADMIN}),
    "teach": frozenset({ROLE_REVIEWER, ROLE_APPROVER, ROLE_ADMIN}),
    "govern": frozenset({ROLE_APPROVER, ROLE_ADMIN}),
    "administer": frozenset({ROLE_ADMIN}),
}


class TenantError(Exception):
    """Base class for tenant-boundary violations."""


class TenantMismatch(TenantError):
    """A store was opened under a different tenant than it was created for."""


class CrossTenantWrite(TenantError):
    """A write tried to place a record outside the store's tenant."""


class PermissionDenied(TenantError):
    """The principal lacks a capability the operation requires."""


@dataclass(frozen=True)
class Principal:
    """Who is acting, within which tenant, holding which capabilities."""

    tenant_id: str
    subject: str
    roles: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "tenant_id", required_text(self.tenant_id, "tenant_id")
        )
        object.__setattr__(self, "subject", required_text(self.subject, "subject"))
        object.__setattr__(self, "roles", frozenset(self.roles))

    def has(self, capability: str) -> bool:
        """Whether this principal holds a named capability."""
        granted = CAPABILITIES.get(capability)
        if granted is None:
            raise KeyError(f"unknown capability: {capability}")
        return bool(self.roles & granted)

    def require(self, capability: str) -> "Principal":
        """Return self when the capability is held; raise `PermissionDenied` if not."""
        if not self.has(capability):
            raise PermissionDenied(
                f"{self.subject} may not {capability} in tenant {self.tenant_id}"
            )
        return self

    def as_event(self) -> dict:
        """The identity fields recorded alongside every durable event."""
        return {
            "tenant": self.tenant_id,
            "reviewer": self.subject,
            "roles": sorted(self.roles),
        }


def local_principal(tenant_id: str = "local") -> Principal:
    """The single-operator principal used by the demo, the CLI, and the console.

    Holds every capability. It trusts whoever runs the process — see the module
    docstring for why that is a seam and not a claim.
    """
    return Principal(tenant_id=tenant_id, subject="local-operator", roles=ALL_ROLES)


def tenant_of_scope(scope: dict) -> str:
    """The tenant named by a record's scope tuple."""
    if not isinstance(scope, dict):
        raise TypeError("scope must be an object")
    return required_text(scope.get("tenant"), "scope.tenant")
