"""Where partners come from (ADR 0006). The service only knows `PartnerSource`; today's
implementation reads JSON exports, a MISA one will replace it."""

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class SourcePartner:
    external_code: str
    name: str
    legal_name: str | None
    tax_code: str | None
    address: str | None
    email: str | None
    phone: str | None
    is_customer: bool
    is_supplier: bool
    is_active: bool
    can_order_before_contract: bool
    raw: dict[str, Any]
    # Fields whose value differs between two records of the same code: {field: [a, b]}.
    mismatches: dict[str, list[str]] = field(default_factory=dict)


class PartnerSource(Protocol):
    name: str

    def fetch(self) -> Sequence[SourcePartner]:
        """Every partner the source currently lists, one record per external code."""
        ...


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _customer(record: dict[str, Any]) -> SourcePartner:
    return SourcePartner(
        external_code=record["code"].strip(),
        name=_clean(record.get("company_name")) or record["code"].strip(),
        legal_name=_clean(record.get("legal_name")),
        tax_code=_clean(record.get("tax_code")),
        address=_clean(record.get("address")),
        email=_clean(record.get("email")),
        phone=_clean(record.get("phone")),
        is_customer=True,
        is_supplier=False,
        is_active=bool(record.get("is_active", True)),
        can_order_before_contract=bool(record.get("can_po_truoc_hd", False)),
        raw={"customer": record},
    )


def _supplier(record: dict[str, Any]) -> SourcePartner:
    code = record["code"].strip()
    name = _clean(record.get("name")) or code
    # Supplier exports prefix the display name with the code ("KH0001 ACME").
    if name.startswith(code + " "):
        name = name[len(code) + 1 :]
    return SourcePartner(
        external_code=code,
        name=name,
        legal_name=_clean(record.get("legal_name")),
        tax_code=_clean(record.get("tax_code")),
        address=_clean(record.get("address")),
        email=_clean(record.get("email")),
        phone=_clean(record.get("phone")),
        is_customer=False,
        is_supplier=True,
        is_active=bool(record.get("is_active", True)),
        can_order_before_contract=False,
        raw={"supplier": record},
    )


_MERGED_FIELDS = ("name", "legal_name", "tax_code", "address", "email", "phone")


def merge(customer: SourcePartner, supplier: SourcePartner) -> SourcePartner:
    """One partner listed in both exports holds both roles. An empty value is filled from the
    other record; two different non-empty values keep the customer one and are reported as a
    mismatch, never silently chosen."""
    values: dict[str, Any] = {}
    mismatches: dict[str, list[str]] = {}
    for name in _MERGED_FIELDS:
        a, b = getattr(customer, name), getattr(supplier, name)
        values[name] = a if a is not None else b
        if a is not None and b is not None and a != b:
            mismatches[name] = [a, b]
    return replace(
        customer,
        **values,
        is_supplier=True,
        is_active=customer.is_active or supplier.is_active,
        raw={**customer.raw, **supplier.raw},
        mismatches=mismatches,
    )


class DuplicateCodeError(ValueError):
    pass


def _by_code(records: Iterable[SourcePartner], file: Path) -> dict[str, SourcePartner]:
    result: dict[str, SourcePartner] = {}
    for record in records:
        if record.external_code in result:
            raise DuplicateCodeError(f"{file}: code {record.external_code} appears twice")
        result[record.external_code] = record
    return result


def _load(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON array of records")
    return data


class JsonFilePartnerSource:
    """Customer and supplier JSON exports. A code in a customer file is a customer, in a supplier
    file a supplier, in both files both. A code repeated inside one role is refused: the export
    is ambiguous and must be fixed, not guessed."""

    name = "json-export"

    def __init__(self, customer_files: Sequence[Path], supplier_files: Sequence[Path]) -> None:
        self.customer_files = customer_files
        self.supplier_files = supplier_files

    def _read(self, files: Sequence[Path], parse: Any) -> dict[str, SourcePartner]:
        merged: dict[str, SourcePartner] = {}
        for file in files:
            for code, record in _by_code(map(parse, _load(file)), file).items():
                if code in merged:
                    raise DuplicateCodeError(f"{file}: code {code} is also in another file")
                merged[code] = record
        return merged

    def fetch(self) -> Sequence[SourcePartner]:
        customers = self._read(self.customer_files, _customer)
        suppliers = self._read(self.supplier_files, _supplier)
        result = [
            merge(record, suppliers[code]) if code in suppliers else record
            for code, record in customers.items()
        ]
        result += [record for code, record in suppliers.items() if code not in customers]
        return result
