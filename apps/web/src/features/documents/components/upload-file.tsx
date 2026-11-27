"use client"

import { Upload04Icon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { useRef } from "react"
import { toast } from "sonner"

import type { DocumentFileRead } from "@workspace/api-client"
import { useHasPermission } from "@workspace/core/auth"
import { useUploadDocumentFile } from "@workspace/core/documents"
import { describeApiError } from "@workspace/core/lib/form"
import { useTranslation } from "@workspace/i18n"

import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"

/** What the API accepts; the browser filter only saves a round trip. */
const ACCEPTED_FILES = ".pdf,.doc,.docx,.xls,.xlsx"

/** Attach a scan, Word or Excel file to a contract's files. */
export function UploadFile({
  setId,
  onUploaded,
}: {
  setId: string
  onUploaded?: (file: DocumentFileRead) => void
}) {
  const { t } = useTranslation()
  const upload = useUploadDocumentFile(setId)
  const canRegister = useHasPermission("contracts:register")
  const input = useRef<HTMLInputElement>(null)
  if (!canRegister) return null
  return (
    <>
      <Button variant="outline" disabled={upload.isPending} onClick={() => input.current?.click()}>
        {upload.isPending ? <Spinner /> : <HugeiconsIcon icon={Upload04Icon} />}
        {t("documents.upload")}
      </Button>
      <input
        ref={input}
        type="file"
        hidden
        aria-label={t("documents.upload")}
        accept={ACCEPTED_FILES}
        disabled={upload.isPending}
        onChange={(event) => {
          const file = event.target.files?.[0]
          event.target.value = ""
          if (!file) return
          upload.mutate(
            { path: { setId }, body: { file } },
            {
              onSuccess: (stored) => {
                toast.success(t("documents.uploaded"))
                onUploaded?.(stored)
              },
              onError: (error) => toast.error(describeApiError(error)),
            }
          )
        }}
      />
    </>
  )
}
