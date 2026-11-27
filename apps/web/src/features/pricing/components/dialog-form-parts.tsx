"use client"

import type { Control, FieldErrors, FieldValues, Path } from "react-hook-form"

import { useTranslation } from "@workspace/i18n"

import { FormInput } from "@/components/design-system/form/form-input"
import { FormRootError } from "@/components/design-system/form/form-root-error"
import { FormTextarea } from "@/components/design-system/form/form-textarea"
import { Button } from "@/components/ui/button"
import { DialogFooter } from "@/components/ui/dialog"

/** Where in the document the entry is printed: the page and the exact wording. */
export function CitationFields<T extends FieldValues & { page: unknown; quote: unknown }>({
  control,
}: {
  control: Control<T>
}) {
  const { t } = useTranslation()
  return (
    <>
      <FormInput
        control={control}
        name={"page" as Path<T>}
        type="number"
        min={1}
        label={t("pricing.page")}
      />
      <FormTextarea control={control} name={"quote" as Path<T>} label={t("pricing.quote")} />
    </>
  )
}

/** The form-level error and the save button closing every pricing dialog. */
export function DialogFormFooter({
  errors,
  isSubmitting,
  submitLabel,
}: {
  errors: FieldErrors
  isSubmitting: boolean
  /** Names the action when it is more than saving ("Approve", "Submit for approval"). */
  submitLabel?: string
}) {
  const { t } = useTranslation()
  return (
    <>
      <FormRootError errors={errors} />
      <DialogFooter>
        <Button type="submit" disabled={isSubmitting}>
          {submitLabel ?? t("pricing.save")}
        </Button>
      </DialogFooter>
    </>
  )
}
