from datetime import date

from app.modules.contracts.schemas import ContractOverview
from app.shared.schemas import Schema


class Overview(Schema):
    on: date
    contracts: ContractOverview
