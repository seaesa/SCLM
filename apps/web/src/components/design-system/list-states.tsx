"use client"

import { useTranslation } from "@workspace/i18n"

import { Button } from "@/components/ui/button"
import { Empty, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"

interface ListStatesProps {
  isPending: boolean
  isError: boolean
  isEmpty: boolean
  onRetry: () => void
  children: React.ReactNode
}

/** Loading skeleton, error with retry, or empty state; the list itself otherwise. */
export function ListStates({ isPending, isError, isEmpty, onRetry, children }: ListStatesProps) {
  const { t } = useTranslation()
  if (isPending) {
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: 5 }, (_, index) => (
          <Skeleton key={index} className="h-10 w-full" />
        ))}
      </div>
    )
  }
  if (isError) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>{t("list.loadError")}</EmptyTitle>
          <Button variant="outline" onClick={onRetry}>
            {t("common.retry")}
          </Button>
        </EmptyHeader>
      </Empty>
    )
  }
  if (isEmpty) {
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyTitle>{t("list.empty")}</EmptyTitle>
        </EmptyHeader>
      </Empty>
    )
  }
  return children
}

/** A row of toggle buttons for list filters. */
export function FilterTabs<K extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: readonly { key: K }[]
  value: K
  onChange: (key: K) => void
  label: (key: K) => string
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map(({ key }) => (
        <Button
          key={key}
          size="sm"
          variant={value === key ? "secondary" : "ghost"}
          onClick={() => onChange(key)}
        >
          {label(key)}
        </Button>
      ))}
    </div>
  )
}
