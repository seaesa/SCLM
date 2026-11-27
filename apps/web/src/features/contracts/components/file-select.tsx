"use client"

import { Controller, type Control, type FieldPath, type FieldValues } from "react-hook-form"

import { useDocumentSet } from "@workspace/core/documents"
import { translateMessage, useTranslation } from "@workspace/i18n"

import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { UploadFile } from "@/features/documents/components/upload-file"

import { RemoveFile } from "./remove-file"

interface FileSelectProps<T extends FieldValues> {
  control: Control<T>
  name: FieldPath<T>
  label: string
  dossierId: string
  /** Given where an unused file may be removed. */
  contractId?: string
}

/** Pick one file of the contract's files, or upload it here (the new file is then picked). */
export function FileSelect<T extends FieldValues>({
  control,
  name,
  label,
  dossierId,
  contractId,
}: FileSelectProps<T>) {
  const { t } = useTranslation()
  const files = useDocumentSet(dossierId).data?.files ?? []
  const items = files.map((file) => ({
    value: file.id,
    label: file.path.split("/").at(-1) ?? file.path,
  }))
  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <Field data-invalid={fieldState.invalid}>
          <FieldLabel htmlFor={name}>{label}</FieldLabel>
          <div className="flex min-w-0 gap-2">
            <Select
              items={items}
              value={field.value === "" ? null : field.value}
              onValueChange={(value) => field.onChange(value ?? "")}
            >
              <SelectTrigger
                id={name}
                aria-invalid={fieldState.invalid}
                className="w-0 min-w-0 flex-1 [&_[data-slot=select-value]]:truncate"
              >
                <SelectValue placeholder={t("contracts.fileSelect.placeholder")} />
              </SelectTrigger>
              <SelectContent>
                {items.map((item) => (
                  <SelectItem
                    key={item.value}
                    value={item.value}
                    className="max-w-[min(32rem,80vw)]"
                  >
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {contractId && field.value ? (
              <RemoveFile
                contractId={contractId}
                dossierId={dossierId}
                fileId={field.value}
                name={items.find((item) => item.value === field.value)?.label ?? ""}
                onRemoved={() => field.onChange("")}
              />
            ) : null}
            <UploadFile setId={dossierId} onUploaded={(file) => field.onChange(file.id)} />
          </div>
          {files.length === 0 ? (
            <FieldDescription>{t("contracts.fileSelect.empty")}</FieldDescription>
          ) : null}
          <FieldError>{translateMessage(fieldState.error?.message)}</FieldError>
        </Field>
      )}
    />
  )
}
