"use client"

import { Controller, type Control, type FieldPath, type FieldValues } from "react-hook-form"

import { translateMessage, useTranslation } from "@workspace/i18n"

import { Field, FieldError, FieldLabel } from "@/components/ui/field"
import { Textarea } from "@/components/ui/textarea"

interface FormTextareaProps<T extends FieldValues> {
  control: Control<T>
  name: FieldPath<T>
  label: string
  rows?: number
}

/** shadcn `Field` + `Textarea` bound to react-hook-form, with translated error display. */
export function FormTextarea<T extends FieldValues>({
  control,
  name,
  label,
  rows = 2,
}: FormTextareaProps<T>) {
  useTranslation() // re-render error messages when the language changes
  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <Field data-invalid={fieldState.invalid}>
          <FieldLabel htmlFor={name}>{label}</FieldLabel>
          <Textarea
            {...field}
            value={field.value ?? ""}
            id={name}
            rows={rows}
            aria-invalid={fieldState.invalid}
          />
          <FieldError>{translateMessage(fieldState.error?.message)}</FieldError>
        </Field>
      )}
    />
  )
}
