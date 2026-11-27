"use client"

import { toast } from "sonner"

import { useRemoveContractFile } from "@workspace/core/contracts"
import { describeApiError } from "@workspace/core/lib/form"
import { useTranslation } from "@workspace/i18n"

import { ConfirmButton } from "@/components/design-system/confirm-button"

interface RemoveFileProps {
  contractId: string
  dossierId: string
  fileId: string
  name: string
  onRemoved: () => void
}

/** Take an uploaded file off the contract; refused while a document uses it. */
export function RemoveFile({ contractId, dossierId, fileId, name, onRemoved }: RemoveFileProps) {
  const { t } = useTranslation()
  const remove = useRemoveContractFile(contractId, dossierId)
  return (
    <ConfirmButton
      trigger={t("contracts.remove.removeFile")}
      title={t("contracts.remove.removeFile")}
      description={t("contracts.remove.removeFileConfirm", { name })}
      confirmLabel={t("contracts.remove.confirm")}
      onConfirm={async () => {
        try {
          await remove.mutateAsync({ path: { contractId, fileId } })
          onRemoved()
        } catch (error) {
          toast.error(describeApiError(error))
          throw error
        }
      }}
    />
  )
}
