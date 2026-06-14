"""Roles and permission groups for multi-role RBAC.

Roles are stored on the user and embedded in the access-token claims. Keep the
permission groups here (in code, reviewable) rather than scattering ``if`` checks
across routers.
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    CANDIDATE = "candidate"
    EMPLOYER_RECRUITER = "employer_recruiter"
    EMPLOYER_ADMIN = "employer_admin"
    UNIVERSITY_STAFF = "university_staff"
    UNIVERSITY_ADMIN = "university_admin"
    PLATFORM_ADMIN = "platform_admin"


# Convenience groups used by route guards.
EMPLOYER_ROLES = frozenset({Role.EMPLOYER_RECRUITER, Role.EMPLOYER_ADMIN})
UNIVERSITY_ROLES = frozenset({Role.UNIVERSITY_STAFF, Role.UNIVERSITY_ADMIN})
ORG_ADMIN_ROLES = frozenset({Role.EMPLOYER_ADMIN, Role.UNIVERSITY_ADMIN})
ALL_STAFF_ROLES = EMPLOYER_ROLES | UNIVERSITY_ROLES | {Role.PLATFORM_ADMIN}
