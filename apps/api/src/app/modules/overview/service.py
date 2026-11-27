from datetime import date

from app.modules.contracts.service import ContractService
from app.modules.overview.schemas import Overview


class OverviewService:
    """Read-only dashboard figures, each computed by the module that owns the data."""

    def __init__(self, contracts: ContractService) -> None:
        self.contracts = contracts

    async def overview(self, on: date) -> Overview:
        return Overview(
            on=on,
            contracts=await self.contracts.overview(),
        )
