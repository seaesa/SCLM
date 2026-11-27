import type {
  ContractCategory,
  Lifecycle,
  PaymentFilter,
  StatementFilter,
} from "@workspace/api-client"
import type { ContractView } from "@workspace/core/contracts"

// Kept out of "use client" modules: server pages read these to parse search params.

export const CONTRACT_CATEGORIES = [
  "customer",
  "contractor",
  "warehouse",
] as const satisfies readonly ContractCategory[]

export const PAYMENT_FILTERS = [
  "up_to_15",
  "up_to_30",
  "up_to_45",
  "over_45",
  "none",
] as const satisfies readonly PaymentFilter[]

export const STATEMENT_FILTERS = [
  "month_end",
  "day_of_month",
  "none",
] as const satisfies readonly StatementFilter[]

export const RENEWAL_FILTERS = ["automatic", "in_cycle", "conditional", "none"] as const

export const LIFECYCLES = [
  "draft",
  "active",
  "expired",
  "terminated",
  "undetermined",
] as const satisfies readonly Lifecycle[]

/** Quick views of the contract list, opened from the dashboard by `?view=`. */
export const CONTRACT_VIEWS = [
  "all",
  "awaiting_approval",
  "awaiting_signature",
  "incomplete",
] as const satisfies readonly ContractView[]

export const isContractView = (value: unknown): value is ContractView =>
  CONTRACT_VIEWS.some((view) => view === value)
