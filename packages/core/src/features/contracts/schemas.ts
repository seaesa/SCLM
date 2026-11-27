import { z } from "zod"

import {
  zInstrumentCreate,
  zReviewDecision,
  zReviewSubmit,
  zSigningWrite,
} from "@workspace/api-client/zod"

/** Inputs give strings; an empty box means "not given". */
const blankToNull = (value: unknown) => (value === "" || value === undefined ? null : value)
const optionalText = (schema: z.ZodString) => z.preprocess(blankToNull, schema.nullable())

export const instrumentFormSchema = zInstrumentCreate.extend({
  fileId: z.string().min(1, { message: "contracts.instrumentDialog.fileRequired" }),
})

export const reviewSubmitFormSchema = zReviewSubmit.extend({
  comment: optionalText(z.string().trim().max(2000)),
})

/** The signed scan is optional in the schema; the API asks for it when a reviewed draft is
 * marked signed by both parties. */
export const signingFormSchema = zSigningWrite.extend({
  fileId: z.preprocess(blankToNull, z.uuid().nullable()),
})

export const reviewDecisionFormSchema = zReviewDecision.extend({
  comment: optionalText(z.string().trim().max(2000)),
})
