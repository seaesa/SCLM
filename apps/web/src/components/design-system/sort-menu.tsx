"use client"

import { Sorting05Icon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"

import { useTranslation } from "@workspace/i18n"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface SortMenuProps<V extends string> {
  value: V
  options: readonly { value: V; label: string }[]
  onChange: (value: V) => void
}

/** The order of a server-sorted list, from a menu next to the column picker. */
export function SortMenu<V extends string>({ value, options, onChange }: SortMenuProps<V>) {
  const { t } = useTranslation()
  const current = options.find((option) => option.value === value)?.label
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="outline" size="sm" />}>
        <HugeiconsIcon icon={Sorting05Icon} data-icon="inline-start" />
        {current}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-auto max-w-80 min-w-48">
        <DropdownMenuGroup>
          <DropdownMenuLabel>{t("filters.sort")}</DropdownMenuLabel>
          <DropdownMenuRadioGroup
            value={value}
            onValueChange={(next: string) => {
              const option = options.find((item) => item.value === next)
              if (option) onChange(option.value)
            }}
          >
            {options.map((option) => (
              <DropdownMenuRadioItem key={option.value} value={option.value}>
                {option.label}
              </DropdownMenuRadioItem>
            ))}
          </DropdownMenuRadioGroup>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
