"use client"

import type { ContractRead } from "@workspace/api-client"
import { formatNumber } from "@workspace/core/lib/number"
import { useTranslation } from "@workspace/i18n"

/** The contract value, or "billed on actual volume" when none is printed. */
export function ContractValue({ contract }: { contract: ContractRead }) {
  const { t } = useTranslation()
  if (contract.valueAmount === null) return <>{t("contracts.choices.actual")}</>
  return <span className="tabular-nums">{formatNumber(Number(contract.valueAmount))} đ</span>
}
