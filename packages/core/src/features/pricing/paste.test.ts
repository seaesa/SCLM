import { describe, expect, it } from "vitest"

import { parsePastedLines } from "./paste"

const row = (...cells: string[]) => cells.join("\t")

describe("parsePastedLines", () => {
  it("reads grouped amounts exactly and falls back to the table page", () => {
    const text = [
      row("Transport", "Depot A", "Port B", "1t truck", "trip", "1.525.700", "", "night"),
      row("Transport", "", "", "", "trip", "1,525,700", "4"),
      row("Storage", "", "", "", "m2", "85000"),
    ].join("\r\n")

    const { lines, issues } = parsePastedLines(text, { defaultPage: 7 })

    expect(issues).toEqual([])
    expect(lines.map((line) => [line.unitPrice, line.page, line.origin, line.note])).toEqual([
      ["1525700", 7, "Depot A", "night"],
      ["1525700", 4, null, null],
      ["85000", 7, null, null],
    ])
  })

  it("rejects an amount it would have to guess, and the whole row with it", () => {
    const text = [
      row("Transport", "", "", "", "trip", "1.5"),
      row("Transport", "", "", "", "trip", "1.525,700"),
      row("", "", "", "", "", "100"),
      row("Transport", "", "", "", "trip", "100", "p3"),
    ].join("\n")

    const { lines, issues } = parsePastedLines(text, { defaultPage: 1 })

    expect(lines).toEqual([])
    expect(issues).toEqual([
      { row: 1, column: "unitPrice", code: "invalid_number" },
      { row: 2, column: "unitPrice", code: "invalid_number" },
      { row: 3, column: "service", code: "required" },
      { row: 3, column: "unit", code: "required" },
      { row: 4, column: "page", code: "invalid_number" },
    ])
  })

  it("skips blank rows and, when asked, the header row", () => {
    const text = [
      "Service\tFrom\tTo\tVehicle\tUnit\tPrice",
      "",
      row("Storage", "", "", "", "m2", "9"),
    ]

    const { lines, issues } = parsePastedLines(text.join("\n"), { defaultPage: 2, hasHeader: true })

    expect(issues).toEqual([])
    expect(lines).toHaveLength(1)
  })
})
