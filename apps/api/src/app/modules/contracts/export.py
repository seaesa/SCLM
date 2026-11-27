"""The addenda list as an Excel sheet, for the people who reconcile prices by period."""

from collections.abc import Sequence
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font

from app.modules.contracts.schemas import InstrumentListItem

# Column headings are part of the file people keep; they are Vietnamese like the UI.
# cspell:disable
_HEADINGS = (
    "Mã hợp đồng",
    "Đối tác",
    "Mã văn bản",
    "Loại",
    "Số",
    "Ngày ký",
    "Hiệu lực từ",
    "Hiệu lực đến",
    "Điều chỉnh",
    "Nội dung",
    "Duyệt",
    "Ký",
    "Người phụ trách",
)
# cspell:enable


def instruments_workbook(items: Sequence[InstrumentListItem]) -> bytes:
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "Phụ lục"
    sheet.append(_HEADINGS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for item in items:
        sheet.append(
            (
                item.contract_code,
                f"{item.partner.code} {item.partner.name}",
                item.code,
                item.kind.value,
                item.number,
                item.signed_on,
                item.effective_from,
                item.effective_to,
                ", ".join(a.value for a in item.adjustments),
                item.summary,
                item.review_state.value if item.review_state else None,
                item.signing_state.value,
                item.owner.name if item.owner else None,
            )
        )
    for column in ("F", "G", "H"):
        for cell in sheet[column][1:]:
            cell.number_format = "dd/mm/yyyy"
    sheet.freeze_panes = "A2"
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()
