import { formatNumber } from "@workspace/core/lib/number"

/** An exact decimal amount from the API ("1525700.00") shown in the reader's grouping. */
export const formatAmount = (amount: string) =>
  formatNumber(Number(amount), { maximumFractionDigits: 2 })

/** A stored fraction ("0.1046") shown as a signed percentage ("+10.46%"). */
export const formatChange = (fraction: string) =>
  formatNumber(Number(fraction), {
    style: "percent",
    maximumFractionDigits: 2,
    signDisplay: "always",
  })

/** A stored fraction ("0.35") shown as a percentage ("35%"). */
export const formatShare = (fraction: string) =>
  formatNumber(Number(fraction), { style: "percent", maximumFractionDigits: 2 })
