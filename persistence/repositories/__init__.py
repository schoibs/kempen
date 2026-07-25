"""Persistence queries scoped to application resources."""
from .assets import AssetRepository
from .campaigns import CampaignRepository

__all__ = ["AssetRepository", "CampaignRepository"]
