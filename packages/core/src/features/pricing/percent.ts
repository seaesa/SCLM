const PERCENT = /^\d{1,3}(?:[.,]\d{1,4})?$/

/**
 * "35" → "0.35", "10,46" → "0.1046". Shifts the decimal point in the text instead of dividing,
 * because 14.3 / 100 is 0.14300000000000002 in floating point. Null when not a percentage.
 */
export function percentToFraction(text: string): string | null {
  const value = text.trim().replace(",", ".")
  if (!PERCENT.test(value)) return null
  const [whole = "", decimals = ""] = value.split(".")
  const digits = whole.padStart(3, "0")
  const fraction = `${Number(digits.slice(0, -2))}.${digits.slice(-2)}${decimals}`
  return fraction.replace(/0+$/, "").replace(/\.$/, "")
}

/** "0.35" → "35", for showing a stored fraction as a percentage. */
export function fractionToPercent(fraction: string): string {
  const [whole = "0", decimals = ""] = fraction.split(".")
  const digits = `${decimals}00`
  const percent = `${Number(`${whole}${digits.slice(0, 2)}`)}.${digits.slice(2)}`
  return percent.replace(/0+$/, "").replace(/\.$/, "")
}
