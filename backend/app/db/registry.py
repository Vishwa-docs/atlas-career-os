"""Import every domain's models so ``Base.metadata`` is fully populated.

Used by Alembic autogenerate and by the test harness (create_all). Keeping this
in one place means adding a new domain needs no edits to a central registry.
"""

from __future__ import annotations

import importlib
import pkgutil


def import_all_models() -> None:
    import app.domains as domains_pkg

    for module in pkgutil.iter_modules(domains_pkg.__path__):
        name = f"app.domains.{module.name}.models"
        try:
            importlib.import_module(name)
        except ModuleNotFoundError:
            continue
