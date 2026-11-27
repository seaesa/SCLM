"use client"

import { ArrowDown01Icon, Cancel01Icon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { useId, useState } from "react"

import type { PartnerRead, PartnerRole } from "@workspace/api-client"
import { usePartnerSearch } from "@workspace/core/partners"
import { useTranslation } from "@workspace/i18n"

import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Spinner } from "@/components/ui/spinner"

import { PartnerSummaryLine } from "./partner-rows"

interface PartnerPickerProps {
  role?: PartnerRole
  value?: PartnerRead
  onChange: (partner?: PartnerRead) => void
}

/** A searchable drop-down of the partners synchronized from the source of record. The search
 * runs on the server (code, name, tax code), so the list is never preloaded. */
export function PartnerPicker({ role, value, onChange }: PartnerPickerProps) {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const listId = useId()
  const [search, setSearch] = useState("")
  const { query, hasTerm } = usePartnerSearch(search, role)
  const partners = query.data?.items ?? []

  return (
    <div className="flex items-center gap-2">
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger
          render={
            <Button
              variant="outline"
              role="combobox"
              aria-expanded={isOpen}
              aria-controls={listId}
              className="h-auto min-h-10 flex-1 justify-between py-2 text-left font-normal"
            />
          }
        >
          {value ? (
            <PartnerSummaryLine partner={value} />
          ) : (
            <span className="text-muted-foreground">{t("partners.pick")}</span>
          )}
          <HugeiconsIcon icon={ArrowDown01Icon} className="shrink-0 opacity-60" />
        </PopoverTrigger>
        <PopoverContent className="w-(--anchor-width) min-w-96 p-0" align="start">
          <Command shouldFilter={false}>
            <CommandInput
              value={search}
              onValueChange={setSearch}
              placeholder={t("partners.searchHint")}
            />
            <CommandList id={listId}>
              <SearchState
                hasTerm={hasTerm}
                isSearching={query.isFetching && partners.length === 0}
              />
              {partners.map((partner) => (
                <CommandItem
                  key={partner.id}
                  value={partner.id}
                  onSelect={() => {
                    onChange(partner)
                    setIsOpen(false)
                  }}
                >
                  <PartnerSummaryLine partner={partner} />
                </CommandItem>
              ))}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {value ? (
        <Button variant="ghost" size="icon" aria-label={t("date.clear")} onClick={() => onChange()}>
          <HugeiconsIcon icon={Cancel01Icon} />
        </Button>
      ) : null}
    </div>
  )
}

function SearchState({ hasTerm, isSearching }: { hasTerm: boolean; isSearching: boolean }) {
  const { t } = useTranslation()
  if (!hasTerm) {
    return (
      <p className="px-3 py-6 text-center text-sm text-muted-foreground">
        {t("partners.typeToSearch")}
      </p>
    )
  }
  if (isSearching) {
    return (
      <div className="flex justify-center py-6">
        <Spinner />
      </div>
    )
  }
  return <CommandEmpty>{t("list.empty")}</CommandEmpty>
}
