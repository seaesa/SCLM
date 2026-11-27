"use client"

import { useState } from "react"
import { Controller } from "react-hook-form"
import { toast } from "sonner"

import type { InstrumentKind } from "@workspace/api-client"
import { useAddInstrumentForm } from "@workspace/core/contracts"
import { useDocumentSet } from "@workspace/core/documents"
import { useTranslation } from "@workspace/i18n"

import { ChoiceSelect } from "@/components/design-system/choice-select"
import { FormRootError } from "@/components/design-system/form/form-root-error"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Field, FieldLabel } from "@/components/ui/field"
import { CAN_ADD_DOCUMENTS } from "@/config"

import { FileSelect } from "./file-select"

/** The contract document comes with the contract; later documents are its annexes. */
const INSTRUMENT_KINDS = [
  "addendum",
  "schedule",
  "termination",
] as const satisfies readonly InstrumentKind[]

const ORIGINS = ["signed", "draft"] as const

interface AddInstrumentDialogProps {
  contractId: string
  dossierId: string
}

export function AddInstrumentDialog(props: AddInstrumentDialogProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  if (!CAN_ADD_DOCUMENTS) return null
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button />}>{t("contracts.addInstrument")}</DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        {open && <AddInstrumentForm {...props} onAdded={() => setOpen(false)} />}
      </DialogContent>
    </Dialog>
  )
}

function AddInstrumentForm({
  contractId,
  dossierId,
  onAdded,
}: AddInstrumentDialogProps & { onAdded: () => void }) {
  const { t } = useTranslation()
  const { form, onSubmit } = useAddInstrumentForm(contractId, {
    kind: "addendum",
    fileId: useDocumentSet(dossierId).data?.files[0]?.id,
    onAdded: () => {
      toast.success(t("contracts.instrumentAdded"))
      onAdded()
    },
  })

  return (
    <form onSubmit={onSubmit} className="flex min-w-0 flex-col gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{t("contracts.addInstrument")}</DialogTitle>
      </DialogHeader>
      <Controller
        control={form.control}
        name="kind"
        render={({ field }) => (
          <Field>
            <FieldLabel>{t("contracts.instrumentDialog.kind")}</FieldLabel>
            <ChoiceSelect
              label={t("contracts.instrumentDialog.kind")}
              value={field.value}
              onChange={(next) => next && field.onChange(next)}
              options={INSTRUMENT_KINDS.map((kind) => ({
                value: kind,
                label: t(`contracts.instrumentKind.${kind}`),
              }))}
              className="w-full"
            />
          </Field>
        )}
      />
      <FileSelect
        control={form.control}
        name="fileId"
        label={t("contracts.instrumentDialog.file")}
        dossierId={dossierId}
        contractId={contractId}
      />
      <Controller
        control={form.control}
        name="needsApproval"
        render={({ field }) => (
          <Field>
            <FieldLabel>{t("contracts.instrumentDialog.origin")}</FieldLabel>
            <ChoiceSelect
              label={t("contracts.instrumentDialog.origin")}
              value={field.value ? "draft" : "signed"}
              onChange={(next) => field.onChange(next === "draft")}
              options={ORIGINS.map((origin) => ({
                value: origin,
                label: t(`contracts.instrumentDialog.${origin}`),
              }))}
              className="w-full"
            />
          </Field>
        )}
      />
      <FormRootError errors={form.formState.errors} />
      <DialogFooter>
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {t("contracts.fieldDialog.save")}
        </Button>
      </DialogFooter>
    </form>
  )
}
