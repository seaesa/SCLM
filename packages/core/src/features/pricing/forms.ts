import type { PriceLineRead } from "@workspace/api-client"

import { useApiForm } from "../../lib/form"
import {
  useCorrectPriceLine,
  useCreateFuelClause,
  useCreateFuelPrice,
  useCreatePriceTable,
} from "./hooks"
import { fractionToPercent } from "./percent"
import {
  fuelClauseFormSchema,
  fuelPriceFormSchema,
  priceLineFormSchema,
  priceTableFormSchema,
  withdrawFormSchema,
} from "./schemas"

interface Saved {
  onSaved?: () => void
}

/** Record a price table printed in a document, citing where it starts. */
export function usePriceTableForm(
  contractId: string,
  { instrumentId, page, onSaved }: Saved & { instrumentId: string; page?: number | null }
) {
  const create = useCreatePriceTable(contractId)
  return useApiForm(priceTableFormSchema, {
    defaultValues: {
      instrumentId,
      effectiveFrom: "",
      effectiveTo: "",
      mode: "replace",
      page: page ?? "",
      quote: "",
      note: "",
    },
    submit: (body) => create.mutateAsync({ body }),
    onSuccess: () => onSaved?.(),
  })
}

/** Correct a price line: the old row is withdrawn and the corrected one takes its place. */
export function usePriceLineForm(
  contractId: string,
  { line, onSaved }: Saved & { line: PriceLineRead }
) {
  const correct = useCorrectPriceLine(contractId)
  return useApiForm(priceLineFormSchema, {
    defaultValues: {
      service: line.service,
      origin: line.origin ?? "",
      destination: line.destination ?? "",
      vehicle: line.vehicle ?? "",
      unit: line.unit,
      unitPrice: line.unitPrice.replace(/\.0+$/, ""),
      currency: line.currency,
      includesVat: line.includesVat,
      page: line.page,
      note: line.note ?? "",
      reason: "",
    },
    submit: (body) => correct.mutateAsync({ path: { lineId: line.id }, body }),
    onSuccess: () => onSaved?.(),
  })
}

/** Record the fuel clause of a document: base price, share of cost, trigger and lag. */
export function useFuelClauseForm(
  contractId: string,
  { instrumentId, onSaved }: Saved & { instrumentId: string }
) {
  const create = useCreateFuelClause(contractId)
  return useApiForm(fuelClauseFormSchema, {
    defaultValues: {
      instrumentId,
      fuelType: "",
      basePrice: "",
      baseOn: "",
      share: "",
      threshold: fractionToPercent("0.1"),
      lagDays: "",
      rounding: "none",
      isCumulative: true,
      page: "",
      quote: "",
    },
    submit: (body) => create.mutateAsync({ body }),
    onSuccess: () => onSaved?.(),
  })
}

/** Record a published fuel price, as read from the supplier's notice. */
export function useFuelPriceForm({ fuelType, onSaved }: Saved & { fuelType?: string }) {
  const create = useCreateFuelPrice()
  return useApiForm(fuelPriceFormSchema, {
    defaultValues: { fuelType: fuelType ?? "", effectiveOn: "", price: "", source: "" },
    submit: (body) => create.mutateAsync({ body }),
    onSuccess: () => onSaved?.(),
  })
}

/** Withdraw a recorded row; a reason is required once the contract is published. */
export function useWithdrawForm(
  withdraw: (reason: string | null) => Promise<unknown>,
  { onSaved }: Saved = {}
) {
  return useApiForm(withdrawFormSchema, {
    defaultValues: { reason: "" },
    submit: ({ reason }) => withdraw(reason ?? null),
    onSuccess: () => onSaved?.(),
  })
}
