"""
A minimal in-memory stand-in for a SQLAlchemy `Session`, used by
`test_auth_flow.py` so the auth flow (register -> login -> me) can be
exercised end-to-end through the real FastAPI app/router/schema/security
code without a real Postgres/PostGIS instance.

This is intentionally narrow: it only understands simple
`db.query(Model).filter(Column == value).first()` chains and
`add`/`commit`/`refresh`/`get`, which is exactly what
`app/api/routers/auth.py` and `get_current_user` use. It does NOT attempt
to emulate joins, `group_by`, or geometry columns, which is why the
project/site flow is instead covered by real-DB integration tests in
`test_integration_db.py` (see that file's module docstring for why:
GeoAlchemy2's `Geometry` column type has no SQLite/in-memory fallback).
"""

from datetime import datetime, timezone
from typing import Any, Callable, List, Optional, Type


class FakeQuery:
    def __init__(
        self, model: Type, store: List[Any], predicate: Optional[Callable] = None
    ):
        self.model = model
        self.store = store
        self.predicate = predicate

    def filter(self, *criteria) -> "FakeQuery":
        def combined(obj: Any) -> bool:
            for crit in criteria:
                col_name = crit.left.key
                expected = crit.right.value
                if getattr(obj, col_name, None) != expected:
                    return False
            return True

        return FakeQuery(self.model, self.store, combined)

    def first(self) -> Optional[Any]:
        for obj in self.store:
            if isinstance(obj, self.model) and (
                self.predicate is None or self.predicate(obj)
            ):
                return obj
        return None

    def all(self) -> List[Any]:
        return [
            obj
            for obj in self.store
            if isinstance(obj, self.model)
            and (self.predicate is None or self.predicate(obj))
        ]


class FakeSession:
    """Stands in for `Session` in `Depends(get_db)`."""

    def __init__(self):
        self.store: List[Any] = []
        self._next_id = 1

    def query(self, model: Type) -> FakeQuery:
        return FakeQuery(model, self.store)

    def add(self, obj: Any) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = self._next_id
            self._next_id += 1
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)
        self.store.append(obj)

    def commit(self) -> None:
        pass

    def refresh(self, obj: Any) -> None:
        pass

    def get(self, model: Type, ident: Any) -> Optional[Any]:
        for obj in self.store:
            if isinstance(obj, model) and obj.id == ident:
                return obj
        return None

    def close(self) -> None:
        pass
