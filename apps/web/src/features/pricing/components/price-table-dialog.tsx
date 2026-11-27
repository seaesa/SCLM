"use client"

import { useState } from "react"
import { Controller } from "react-hook-form"
import { toast } from "sonner"

import type { InstrumentRead, TableMode } from "@workspace/api-client"
import { usePriceTableForm } from "@workspace/core/pricing"
import { useTranslation } from "@workspace/i18n"

import { FormDate } from "@/components/design-system/form/form-date"
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
import { Field, FieldLabel } from "@/components/ui/field"

import { CitationFields, DialogFormFooter } from "./dialog-form-parts"
import { InstrumentSelect } from "./instrument-select"

const TABLE_MODES = [{ key: "replace" }, { key: "amend" }] as const satisfies readonly {
  key: TableMode
}[]

interface PriceTableDialogProps {
  contractId: string
  instruments: InstrumentRead[]
}

export function PriceTableDialog(props: PriceTableDialogProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="sm" />}>{t("pricing.addTable")}</DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        {open && <PriceTableForm {...props} onSaved={() => setOpen(false)} />}
      </DialogContent>
    </Dialog>
  )
}

function PriceTableForm({
  contractId,
  instruments,
  onSaved,
}: PriceTableDialogProps & { onSaved: () => void }) {
  const { t } = useTranslation()
  const last = instruments.at(-1)
  const { form, onSubmit } = usePriceTableForm(contractId, {
    instrumentId: last?.id ?? "",
    onSaved: () => {
      toast.success(t("pricing.tableAdded"))
      onSaved()
    },
  })
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{t("pricing.addTable")}</DialogTitle>
      </DialogHeader>
      <InstrumentSelect control={form.control} name="instrumentId" instruments={instruments} />
      <div className="grid grid-cols-2 gap-3">
        <FormDate control={form.control} name="effectiveFrom" label={t("pricing.effectiveFrom")} />
        <FormDate control={form.control} name="effectiveTo" label={t("pricing.effectiveTo")} />
      </div>
      <Field>
        <FieldLabel>{t("pricing.modeLabel")}</FieldLabel>
        <Controller
          control={form.control}
          name="mode"
          render={({ field }) => (
            <FilterTabs
              options={TABLE_MODES}
              value={field.value}
              onChange={field.onChange}
              label={(key) => t(`pricing.mode.${key}`)}
            />
          )}
        />
      </Field>
      <CitationFields control={form.control} />
      <FormTextarea control={form.control} name="note" label={t("pricing.columns.note")} />
      <DialogFormFooter errors={form.formState.errors} isSubmitting={form.formState.isSubmitting} />
    </form>
  )
}
