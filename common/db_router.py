"""Database routing for the two-domain architecture."""

from __future__ import annotations

COMMERCIAL_APPS = {"ordering", "billing", "notification"}
LOGISTICS_APPS = {"inventory", "shipping"}


class DomainDatabaseRouter:
    """Route commercial and logistics apps to their dedicated databases."""

    def db_for_read(self, model, **hints):
        del hints
        return self._resolve_read_db(model._meta.app_label)

    def db_for_write(self, model, **hints):
        del hints
        return self._resolve_write_db(model._meta.app_label)

    def allow_relation(self, obj1, obj2, **hints):
        del hints
        db_list = {self._resolve_db(obj1._meta.app_label), self._resolve_db(obj2._meta.app_label)}
        return len(db_list) == 1

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        del model_name, hints
        target_db = self._resolve_db(app_label)
        return target_db == db

    @staticmethod
    def _resolve_db(app_label: str) -> str:
        if app_label in COMMERCIAL_APPS:
            return "commercial"
        if app_label in LOGISTICS_APPS:
            return "logistics"
        return "default"

    @classmethod
    def _resolve_read_db(cls, app_label: str) -> str:
        return cls._resolve_db(app_label)

    @classmethod
    def _resolve_write_db(cls, app_label: str) -> str:
        return cls._resolve_db(app_label)
