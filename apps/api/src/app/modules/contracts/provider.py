from dishka import Provider, Scope, provide

from app.modules.contracts.repository import (
    CodeCounterRepository,
    ContractEventRepository,
    ContractRepository,
    FieldValueRepository,
    InstrumentRepository,
)
from app.modules.contracts.service import ContractService


class ContractsProvider(Provider):
    scope = Scope.REQUEST

    contracts = provide(ContractRepository)
    instruments = provide(InstrumentRepository)
    values = provide(FieldValueRepository)
    events = provide(ContractEventRepository)
    counters = provide(CodeCounterRepository)
    service = provide(ContractService)
