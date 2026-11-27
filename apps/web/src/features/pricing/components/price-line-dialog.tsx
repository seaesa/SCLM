"use client"

import { useState } from "react"
import { toast } from "sonner"

import type { PriceLineRead } from "@workspace/api-client"
import { usePriceLineForm } from "@workspace/core/pricing"
import { useTranslation } from "@workspace/i18n"

import { FormInput } from "@/components/design-system/form/form-input"
import { FormTextarea } from "@/components/design-system/form/form-textarea"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

import { DialogFormFooter } from "./dialog-form-parts"

interface PriceLineDialogProps {
  contractId: string
  line: PriceLineRead
  isPublished: boolean
}

export function PriceLineDialog(props: PriceLineDialogProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="sm" variant="ghost" />}>
        {t("pricing.correct")}
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        {open && <PriceLineForm {...props} onSaved={() => setOpen(false)} />}
      </DialogContent>
    </Dialog>
  )
}

function PriceLineForm({
  contractId,
  line,
  isPublished,
  onSaved,
}: PriceLineDialogProps & { onSaved: () => void }) {
  const { t } = useTranslation()
  const { form, onSubmit } = usePriceLineForm(contractId, {
    line,
    onSaved: () => {
      toast.success(t("pricing.saved"))
      onSaved()
    },
  })
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{t("pricing.correctTitle")}</DialogTitle>
      </DialogHeader>
      <FormInput control={form.control} name="service" label={t("pricing.columns.service")} />
      <div className="grid grid-cols-2 gap-3">
        <FormInput control={form.control} name="origin" label={t("pricing.columns.origin")} />
        <FormInput
          control={form.control}
          name="destination"
          label={t("pricing.columns.destination")}
        />
        <FormInput control={form.control} name="vehicle" label={t("pricing.columns.vehicle")} />
        <FormInput control={form.control} name="unit" label={t("pricing.columns.unit")} />
        <FormInput
          control={form.control}
          name="unitPrice"
          inputMode="numeric"
          label={t("pricing.columns.unitPrice")}
        />
        <FormInput
          control={form.control}
          name="page"
          type="number"
          min={1}
          label={t("pricing.page")}
        />
      </div>
      <FormTextarea control={form.control} name="note" label={t("pricing.columns.note")} />
      {isPublished && (
        <FormTextarea control={form.control} name="reason" label={t("pricing.reason")} />
      )}
      <DialogFormFooter errors={form.formState.errors} isSubmitting={form.formState.isSubmitting} />
    </form>
  )
}
