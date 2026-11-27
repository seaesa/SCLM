import { describe, expect, it } from "vitest"

import { fractionToPercent, percentToFraction } from "./percent"

describe("percentToFraction", () => {
  it("shifts the decimal point exactly", () => {
    expect(["35", "10,46", "14.3", "5", "100", "0.5"].map(percentToFraction)).toEqual([
      "0.35",
      "0.1046",
      "0.143",
      "0.05",
      "1",
      "0.005",
    ])
  })

  it("refuses text that is not a percentage", () => {
    expect(["", "abc", "35%", "1.2.3", "-5"].map(percentToFraction)).toEqual([
      null,
      null,
      null,
      null,
      null,
    ])
  })

  it("round-trips stored fractions", () => {
    expect(["0.35", "0.1046", "1", "0.100"].map(fractionToPercent)).toEqual([
      "35",
      "10.46",
      "100",
      "10",
    ])
  })
})
