"use client"

import { useRouter } from "next/navigation"
import { toast } from "sonner"

import { useDeleteContract } from "@workspace/core/contracts"
import { describeApiError } from "@workspace/core/lib/form"
import { useTranslation } from "@workspace/i18n"

import { ConfirmButton } from "@/components/design-system/confirm-button"

/** Only a contract with nothing approved or signed can go; the list is shown afterwards. */
export function DeleteContractButton({ contractId }: { contractId: string }) {
  const { t } = useTranslation()
  const router = useRouter()
  const remove = useDeleteContract()
  return (
    <ConfirmButton
      trigger={t("contracts.remove.deleteContract")}
      title={t("contracts.remove.deleteContract")}
      description={t("contracts.remove.deleteContractConfirm")}
      confirmLabel={t("contracts.remove.confirm")}
      onConfirm={async () => {
        try {
          await remove.mutateAsync({ path: { contractId } })
          toast.success(t("contracts.remove.deleted"))
          router.push("/contracts")
        } catch (error) {
          toast.error(describeApiError(error))
          throw error
        }
      }}
    />
  )
}
