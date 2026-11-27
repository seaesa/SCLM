"use client"

import type { MissingFact } from "@workspace/api-client"
import { useTranslation } from "@workspace/i18n"

import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

/** How many key facts are missing, naming each one on hover. */
export function MissingFactsBadge({ facts }: { facts: MissingFact[] }) {
  const { t } = useTranslation()
  if (facts.length === 0) return null
  return (
    <Tooltip>
      <TooltipTrigger render={<Badge variant="destructive" />}>
        {t("contracts.missingFacts", { count: facts.length })}
      </TooltipTrigger>
      <TooltipContent className="flex max-w-80 flex-col items-start gap-0.5">
        {facts.map((fact) => (
          <span key={`${fact.code ?? fact.kind}-${fact.key}`}>
            <span className="font-mono">
              {fact.code ?? t(`contracts.instrumentKind.${fact.kind}`)}
            </span>
            {": "}
            {t(`contracts.fields.${fact.key}`)}
          </span>
        ))}
      </TooltipContent>
    </Tooltip>
  )
}
