from app.modules.seed.models import SeedRun
from app.shared.repository import BaseRepository


class SeedRunRepository(BaseRepository[SeedRun]):
    model = SeedRun

    async def of_step(self, step: str) -> SeedRun | None:
        return await self.find_one(SeedRun.step == step)
