import { z } from "zod"

import {
  zFuelClauseWrite,
  zFuelPriceWrite,
  zPriceLineCorrection,
  zPriceTableWrite,
  zWithdrawRequest,
} from "@workspace/api-client/zod"

import { parseAmount } from "./paste"
import { percentToFraction } from "./percent"

/** Inputs give strings; an empty box means "not given". */
const blankToNull = (value: unknown) => (value === "" || value === undefined ? null : value)
const optionalText = (schema: z.ZodString) => z.preprocess(blankToNull, schema.nullable())
const page = z.coerce.number().int().min(1)
const reason = optionalText(z.string().trim().min(3).max(1000))

/** Whole dong, typed with or without thousands separators, sent as exact digits. */
const amount = z.string().transform((text, context) => {
  const parsed = parseAmount(text)
  if (parsed === null || parsed === "0") {
    context.addIssue({ code: "custom", message: "validation.invalidAmount" })
    return z.NEVER
  }
  return parsed
})

/** A percentage typed by a person ("35"), sent as the fraction the contract means ("0.35"). */
const percent = z.string().transform((text, context) => {
  const fraction = percentToFraction(text)
  if (fraction === null || fraction === "0") {
    context.addIssue({ code: "custom", message: "validation.invalidPercent" })
    return z.NEVER
  }
  return fraction
})

export const priceTableFormSchema = zPriceTableWrite.extend({
  effectiveTo: z.preprocess(blankToNull, z.iso.date().nullable()),
  page,
  quote: optionalText(z.string().trim().max(2000)),
  note: optionalText(z.string().trim().max(2000)),
})

export const priceLineFormSchema = zPriceLineCorrection.extend({
  service: z.string().trim().min(1).max(200),
  origin: optionalText(z.string().trim().max(200)),
  destination: optionalText(z.string().trim().max(200)),
  vehicle: optionalText(z.string().trim().max(100)),
  unit: z.string().trim().min(1).max(50),
  unitPrice: amount,
  page,
  note: optionalText(z.string().trim().max(2000)),
  reason,
})

export const fuelClauseFormSchema = zFuelClauseWrite.extend({
  fuelType: z.string().trim().min(1).max(100),
  basePrice: amount,
  share: percent,
  threshold: percent,
  lagDays: z.coerce.number().int().min(0).max(90),
  page,
  quote: optionalText(z.string().trim().max(2000)),
})

export const fuelPriceFormSchema = zFuelPriceWrite.extend({
  fuelType: z.string().trim().min(1).max(100),
  price: amount,
  source: optionalText(z.string().trim().max(500)),
})

export const withdrawFormSchema = zWithdrawRequest.extend({ reason })
