import type { PriceLineWrite } from "@workspace/api-client"

/** Column order a pasted Excel block must follow (one price line per row). */
export const PASTE_COLUMNS = [
  "service",
  "origin",
  "destination",
  "vehicle",
  "unit",
  "unitPrice",
  "page",
  "note",
] as const

export type PasteColumn = (typeof PASTE_COLUMNS)[number]

export interface PasteIssue {
  row: number
  column: PasteColumn
  code: "required" | "invalid_number"
}

export interface PasteResult {
  lines: PriceLineWrite[]
  issues: PasteIssue[]
}

// Whole dong only, either bare digits or grouped by a single consistent separator
// ("1525700", "1.525.700", "1,525,700", "1 525 700"). Anything else is rejected rather than
// guessed: "1.5" could be 1,5 or 15 depending on who typed it.
const AMOUNT = /^(?:\d+|\d{1,3}(?:\.\d{3})+|\d{1,3}(?:,\d{3})+|\d{1,3}(?: \d{3})+)$/
const PAGE = /^\d+$/

/** An amount in whole dong as plain digits, or null when it cannot be read without guessing. */
export function parseAmount(text: string): string | null {
  const value = text.trim()
  return AMOUNT.test(value) ? value.replaceAll(/[., ]/g, "") : null
}

function cell(cells: string[], column: PasteColumn) {
  const value = cells[PASTE_COLUMNS.indexOf(column)]?.trim() ?? ""
  return value === "" ? null : value
}

/** Parse rows copied from Excel (tab-separated). Rows with any issue produce no line. */
export function parsePastedLines(
  text: string,
  { defaultPage, hasHeader = false }: { defaultPage: number; hasHeader?: boolean }
): PasteResult {
  const rows = text
    .replaceAll("\r\n", "\n")
    .split("\n")
    .map((row, index) => ({ cells: row.split("\t"), row: index + 1 }))
    .filter(({ cells }) => cells.some((value) => value.trim() !== ""))
    .slice(hasHeader ? 1 : 0)

  const lines: PriceLineWrite[] = []
  const issues: PasteIssue[] = []
  for (const { cells, row } of rows) {
    const rowIssues: PasteIssue[] = []
    const service = cell(cells, "service")
    const unit = cell(cells, "unit")
    const amount = cell(cells, "unitPrice")
    const page = cell(cells, "page")
    if (service === null) rowIssues.push({ row, column: "service", code: "required" })
    if (unit === null) rowIssues.push({ row, column: "unit", code: "required" })
    if (amount === null) rowIssues.push({ row, column: "unitPrice", code: "required" })
    else if (parseAmount(amount) === null)
      rowIssues.push({ row, column: "unitPrice", code: "invalid_number" })
    if (page !== null && !PAGE.test(page))
      rowIssues.push({ row, column: "page", code: "invalid_number" })

    if (rowIssues.length > 0 || service === null || unit === null || amount === null) {
      issues.push(...rowIssues)
      continue
    }
    lines.push({
      service,
      origin: cell(cells, "origin"),
      destination: cell(cells, "destination"),
      vehicle: cell(cells, "vehicle"),
      unit,
      unitPrice: parseAmount(amount) ?? amount,
      page: page === null ? defaultPage : Number(page),
      note: cell(cells, "note"),
    })
  }
  return { lines, issues }
}
