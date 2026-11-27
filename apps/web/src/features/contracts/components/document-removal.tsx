"use client"

import { toast } from "sonner"

import type { InstrumentRead } from "@workspace/api-client"
import { useDeleteInstrument } from "@workspace/core/contracts"
import { describeApiError } from "@workspace/core/lib/form"
import { useTranslation } from "@workspace/i18n"

import { ConfirmButton } from "@/components/design-system/confirm-button"

interface DocumentRemovalProps {
  contractId: string
  instrument: InstrumentRead
  next?: string
  onRemoved: (instrumentId: string) => void
}

/** Delete a document entered by mistake; one in review is locked until it is decided. */
export function DocumentRemoval({ contractId, instrument, next, onRemoved }: DocumentRemovalProps) {
  const { t } = useTranslation()
  const remove = useDeleteInstrument(contractId)
  if (!instrument.canDelete) return null
  const name = instrument.code ?? t(`contracts.instrumentKind.${instrument.kind}`)
  const handleConfirm = async () => {
    try {
      await remove.mutateAsync({ path: { instrumentId: instrument.id } })
      toast.success(t("contracts.remove.deleted"))
      if (next) onRemoved(next)
    } catch (error) {
      toast.error(describeApiError(error))
      throw error
    }
  }
  return (
    <ConfirmButton
      trigger={t("contracts.remove.deleteDocument")}
      title={t("contracts.remove.deleteDocument")}
      description={t("contracts.remove.deleteDocumentConfirm", { name })}
      confirmLabel={t("contracts.remove.confirm")}
      onConfirm={handleConfirm}
    />
  )
}
