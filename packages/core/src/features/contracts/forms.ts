import type { InstrumentKind, InstrumentRead } from "@workspace/api-client"

import { useApiForm } from "../../lib/form"
import {
  useAddContractInstrument,
  useApproveInstrument,
  useRejectInstrument,
  useSetInstrumentSigning,
  useSubmitInstrument,
} from "./hooks"
import {
  instrumentFormSchema,
  reviewDecisionFormSchema,
  reviewSubmitFormSchema,
  signingFormSchema,
} from "./schemas"

/** Enter, change or clear the facts of one document, saved together. */
/** Record a document of the contract (the contract, a schedule, an addendum, a termination). */
export function useAddInstrumentForm(
  contractId: string,
  { kind, fileId, onAdded }: { kind: InstrumentKind; fileId?: string; onAdded?: () => void }
) {
  const add = useAddContractInstrument(contractId)
  return useApiForm(instrumentFormSchema, {
    defaultValues: {
      kind,
      fileId: fileId ?? "",
      needsApproval: false,
    },
    submit: (body) => add.mutateAsync({ path: { contractId }, body }),
    onSuccess: () => onAdded?.(),
  })
}

/** Send a document Spider drafted (the contract or an addendum) for approval. */
export function useSubmitInstrumentForm(
  contractId: string,
  { instrument, onSent }: { instrument: InstrumentRead; onSent?: () => void }
) {
  const submitInstrument = useSubmitInstrument(contractId)
  return useApiForm(reviewSubmitFormSchema, {
    defaultValues: { fileId: instrument.fileId, comment: "" },
    submit: (body) => submitInstrument.mutateAsync({ path: { instrumentId: instrument.id }, body }),
    onSuccess: () => onSent?.(),
  })
}

/** Approve or reject a submitted document; a rejection must say what to change. */
export function useReviewDecisionForm(
  contractId: string,
  {
    instrumentId,
    decision,
    onDecided,
  }: { instrumentId: string; decision: "approve" | "reject"; onDecided?: () => void }
) {
  const approve = useApproveInstrument(contractId)
  const reject = useRejectInstrument(contractId)
  const mutation = decision === "approve" ? approve : reject
  return useApiForm(reviewDecisionFormSchema, {
    defaultValues: { comment: "" },
    submit: (body) => mutation.mutateAsync({ path: { instrumentId }, body }),
    onSuccess: () => onDecided?.(),
  })
}

/** Record how far signing has got; the last step names the scan signed by both parties. */
export function useSigningForm(
  contractId: string,
  { instrument, onSaved }: { instrument: InstrumentRead; onSaved?: () => void }
) {
  const setSigning = useSetInstrumentSigning(contractId)
  return useApiForm(signingFormSchema, {
    defaultValues: { state: instrument.signingState, fileId: "" },
    submit: (body) => setSigning.mutateAsync({ path: { instrumentId: instrument.id }, body }),
    onSuccess: () => onSaved?.(),
  })
}
