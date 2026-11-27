"use client"

import { useState } from "react"
import { toast } from "sonner"

import type { ContractEventRead, InstrumentRead, SigningState } from "@workspace/api-client"
import { useHasPermission } from "@workspace/core/auth"
import {
  useReviewDecisionForm,
  useSigningForm,
  useSubmitInstrumentForm,
} from "@workspace/core/contracts"
import { useTranslation } from "@workspace/i18n"

import { FormTextarea } from "@/components/design-system/form/form-textarea"
import { FilterTabs } from "@/components/design-system/list-states"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { DialogFormFooter } from "@/features/pricing/components/dialog-form-parts"

import { FileSelect } from "./file-select"
import { InstrumentStateBadges } from "./instrument-state-badges"

const SIGNING_STATES = [
  { key: "unsigned" },
  { key: "spider_signed" },
  { key: "partner_signed" },
  { key: "signed" },
] as const satisfies readonly { key: SigningState }[]

interface WorkflowProps {
  contractId: string
  instrument: InstrumentRead
  events: ContractEventRead[]
  dossierId: string
}

/**
 * Proposal → approval → signatures of one document. A document Spider did not draft (an archive
 * scan, the partner's own paper) has no review and is shown as signed.
 */
export function InstrumentWorkflow({ contractId, instrument, events, dossierId }: WorkflowProps) {
  const { t } = useTranslation()
  const canRegister = useHasPermission("contracts:register")
  const canApprove = useHasPermission("contracts:approve")
  const review = instrument.reviewState
  if (review === null && instrument.signingState === "signed") return null
  const last = latestStep(events, instrument.id)
  const canSubmit = canRegister && (review === "draft" || review === "rejected")
  const canDecide = canApprove && review === "submitted"
  const canSign = canRegister && (review === null || review === "approved")

  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-muted/30 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <InstrumentStateBadges reviewState={review} signingState={instrument.signingState} />
        {instrument.proposedByName ? (
          <span className="text-muted-foreground">
            {t("contracts.review.proposedBy", { name: instrument.proposedByName })}
          </span>
        ) : null}
        {instrument.approvedByName ? (
          <span className="text-muted-foreground">
            · {t("contracts.review.approvedBy", { name: instrument.approvedByName })}
          </span>
        ) : null}
      </div>
      {last?.comment ? (
        <blockquote className="border-l-2 pl-3 italic">
          {last.comment}
          {last.actorName ? (
            <span className="text-muted-foreground not-italic"> — {last.actorName}</span>
          ) : null}
        </blockquote>
      ) : null}
      {canSubmit || canDecide || canSign ? (
        <div className="flex flex-wrap gap-2">
          {canSubmit ? (
            <SubmitDialog contractId={contractId} instrument={instrument} dossierId={dossierId} />
          ) : null}
          {canDecide ? (
            <DecisionDialog
              contractId={contractId}
              instrumentId={instrument.id}
              decision="approve"
            />
          ) : null}
          {canDecide ? (
            <DecisionDialog
              contractId={contractId}
              instrumentId={instrument.id}
              decision="reject"
            />
          ) : null}
          {canSign ? (
            <SigningDialog contractId={contractId} instrument={instrument} dossierId={dossierId} />
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

/** The latest review step of this document (events are oldest first). */
function latestStep(events: ContractEventRead[], instrumentId: string) {
  let latest: ContractEventRead | undefined
  for (const event of events) {
    if (event.instrumentId === instrumentId) latest = event
  }
  return latest
}

type DocumentProps = Omit<WorkflowProps, "events">

function useDialog() {
  const [open, setOpen] = useState(false)
  return { open, setOpen, close: () => setOpen(false) }
}

function SubmitDialog(props: DocumentProps) {
  const { t } = useTranslation()
  const dialog = useDialog()
  return (
    <Dialog open={dialog.open} onOpenChange={dialog.setOpen}>
      <DialogTrigger render={<Button size="sm" />}>{t("contracts.review.submit")}</DialogTrigger>
      <DialogContent>
        {dialog.open && <SubmitForm {...props} onDone={dialog.close} />}
      </DialogContent>
    </Dialog>
  )
}

function SubmitForm({
  contractId,
  instrument,
  dossierId,
  onDone,
}: DocumentProps & { onDone: () => void }) {
  const { t } = useTranslation()
  const { form, onSubmit } = useSubmitInstrumentForm(contractId, {
    instrument,
    onSent: () => {
      toast.success(t("contracts.review.submitted"))
      onDone()
    },
  })
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{t("contracts.review.submit")}</DialogTitle>
      </DialogHeader>
      <FileSelect
        control={form.control}
        name="fileId"
        label={t("contracts.review.draftFile")}
        dossierId={dossierId}
      />
      <FormTextarea control={form.control} name="comment" label={t("contracts.review.comment")} />
      <DialogFormFooter
        errors={form.formState.errors}
        isSubmitting={form.formState.isSubmitting}
        submitLabel={t("contracts.review.submit")}
      />
    </form>
  )
}

const DECIDED_TOAST = {
  approve: "contracts.review.approved",
  reject: "contracts.review.rejected",
} as const

interface DecisionProps {
  contractId: string
  instrumentId: string
  decision: "approve" | "reject"
}

function DecisionDialog(props: DecisionProps) {
  const { t } = useTranslation()
  const dialog = useDialog()
  return (
    <Dialog open={dialog.open} onOpenChange={dialog.setOpen}>
      <DialogTrigger
        render={<Button size="sm" variant={props.decision === "approve" ? "default" : "outline"} />}
      >
        {t(`contracts.review.${props.decision}`)}
      </DialogTrigger>
      <DialogContent>
        {dialog.open && <DecisionForm {...props} onDone={dialog.close} />}
      </DialogContent>
    </Dialog>
  )
}

function DecisionForm({
  contractId,
  instrumentId,
  decision,
  onDone,
}: DecisionProps & { onDone: () => void }) {
  const { t } = useTranslation()
  const { form, onSubmit } = useReviewDecisionForm(contractId, {
    instrumentId,
    decision,
    onDecided: () => {
      toast.success(t(DECIDED_TOAST[decision]))
      onDone()
    },
  })
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{t(`contracts.review.${decision}`)}</DialogTitle>
      </DialogHeader>
      <FormTextarea
        control={form.control}
        name="comment"
        label={t("contracts.review.comment")}
        rows={3}
      />
      <DialogFormFooter
        errors={form.formState.errors}
        isSubmitting={form.formState.isSubmitting}
        submitLabel={t(`contracts.review.${decision}`)}
      />
    </form>
  )
}

function SigningDialog(props: DocumentProps) {
  const { t } = useTranslation()
  const dialog = useDialog()
  return (
    <Dialog open={dialog.open} onOpenChange={dialog.setOpen}>
      <DialogTrigger render={<Button size="sm" variant="outline" />}>
        {t("contracts.signing.update")}
      </DialogTrigger>
      <DialogContent>
        {dialog.open && <SigningForm {...props} onDone={dialog.close} />}
      </DialogContent>
    </Dialog>
  )
}

function SigningForm({
  contractId,
  instrument,
  dossierId,
  onDone,
}: DocumentProps & { onDone: () => void }) {
  const { t } = useTranslation()
  const { form, onSubmit } = useSigningForm(contractId, {
    instrument,
    onSaved: () => {
      toast.success(t("contracts.signing.saved"))
      onDone()
    },
  })
  const state = form.watch("state")
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{t("contracts.signing.update")}</DialogTitle>
      </DialogHeader>
      <FilterTabs
        options={SIGNING_STATES}
        value={state}
        onChange={(value) => form.setValue("state", value)}
        label={(key) => t(`contracts.signing.state.${key}`)}
      />
      {state === "signed" && instrument.reviewState !== null ? (
        <FileSelect
          control={form.control}
          name="fileId"
          label={t("contracts.signing.signedCopy")}
          dossierId={dossierId}
        />
      ) : null}
      <DialogFormFooter
        errors={form.formState.errors}
        isSubmitting={form.formState.isSubmitting}
        submitLabel={t("contracts.signing.update")}
      />
    </form>
  )
}
