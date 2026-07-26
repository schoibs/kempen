from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from persistence.models import Asset


class AssetRepository:
    """Tenant- and owner-scoped asset queries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, asset: Asset) -> None:
        self.session.add(asset)

    def get_owned(self, *, asset_id: str, tenant_id: str, owner_id: str) -> Asset | None:
        return self.session.scalar(
            select(Asset).where(
                Asset.id == asset_id,
                Asset.tenant_id == tenant_id,
                Asset.owner_id == owner_id,
            )
        )
