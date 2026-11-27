"use client"

import { Cancel01Icon, PlusSignCircleIcon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { addDays, format, isValid, parseISO } from "date-fns"
import { useState, type ReactNode } from "react"
import type { DateRange } from "react-day-picker"

import { dateLocale, todayIso } from "@workspace/core/lib/date"
import { useTranslation } from "@workspace/i18n"

import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

/** ISO dates; either end may be open. */
interface IsoRange {
  from?: string
  to?: string
}

const ISO = "yyyy-MM-dd"
const DISPLAY = "dd/MM/yyyy"
const START_MONTH = new Date(2005, 0)
const END_MONTH = new Date(new Date().getFullYear() + 15, 11)

const fromIso = (value?: string) => {
  const date = value ? parseISO(value) : undefined
  return date && isValid(date) ? date : undefined
}
const show = (value?: string) => {
  const date = fromIso(value)
  return date ? format(date, DISPLAY) : "…"
}

interface FilterButtonProps extends React.ComponentProps<typeof Button> {
  label: string
  /** What the filter is set to; nothing while it is off. */
  current?: ReactNode
}

/** A toolbar filter: a dashed "+ label" while off, "label | value" while on. */
function FilterButton({ label, current, className, ...props }: FilterButtonProps) {
  const isOn = current !== undefined
  return (
    <Button
      variant="outline"
      size="sm"
      className={cn(isOn ? "rounded-r-none border-r-0" : "border-dashed", className)}
      {...props}
    >
      {isOn ? null : <HugeiconsIcon icon={PlusSignCircleIcon} data-icon="inline-start" />}
      {label}
      {isOn ? (
        <>
          <Separator orientation="vertical" className="mx-1 h-4" />
          <span className="max-w-48 truncate font-normal text-primary">{current}</span>
        </>
      ) : null}
    </Button>
  )
}

/** The × beside a filter that is on. */
function ClearButton({ label, onClear }: { label: string; onClear: () => void }) {
  const { t } = useTranslation()
  return (
    <Button
      variant="outline"
      size="icon-sm"
      className="rounded-l-none"
      aria-label={t("filters.clear", { label })}
      onClick={onClear}
    >
      <HugeiconsIcon icon={Cancel01Icon} />
    </Button>
  )
}

interface ChoiceFilterProps<V extends string> {
  label: string
  value?: V
  options: readonly { value: V; label: string }[]
  onChange: (value?: V) => void
}

/** Pick one value from a short list, from a menu under the toolbar button. */
export function ChoiceFilter<V extends string>({
  label,
  value,
  options,
  onChange,
}: ChoiceFilterProps<V>) {
  const { t } = useTranslation()
  const current = options.find((option) => option.value === value)?.label
  return (
    <div className="flex items-center">
      <DropdownMenu>
        <DropdownMenuTrigger render={<FilterButton label={label} current={current} />} />
        <DropdownMenuContent align="start" className="w-auto max-w-80 min-w-48">
          <DropdownMenuRadioGroup
            value={value ?? ""}
            onValueChange={(next: string) =>
              onChange(options.find((option) => option.value === next)?.value)
            }
          >
            {options.map((option) => (
              <DropdownMenuRadioItem key={option.value} value={option.value}>
                {option.label}
              </DropdownMenuRadioItem>
            ))}
          </DropdownMenuRadioGroup>
          {value === undefined ? null : (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => onChange()}>{t("filters.reset")}</DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
      {current === undefined ? null : <ClearButton label={label} onClear={() => onChange()} />}
    </div>
  )
}

interface MultiChoiceFilterProps<V extends string> {
  label: string
  value: readonly V[]
  options: readonly { value: V; label: string }[]
  onChange: (value: V[]) => void
}

/** Tick any number of values; the menu stays open so several can be ticked in a row. */
export function MultiChoiceFilter<V extends string>({
  label,
  value,
  options,
  onChange,
}: MultiChoiceFilterProps<V>) {
  const { t } = useTranslation()
  const chosen = options.filter((option) => value.includes(option.value))
  const current = chosen.length > 0 ? chosen.map((option) => option.label).join(", ") : undefined
  const toggle = (option: V, isChecked: boolean) =>
    onChange(
      options.map((o) => o.value).filter((v) => (v === option ? isChecked : value.includes(v)))
    )
  return (
    <div className="flex items-center">
      <DropdownMenu>
        <DropdownMenuTrigger render={<FilterButton label={label} current={current} />} />
        <DropdownMenuContent align="start" className="w-auto max-w-80 min-w-48">
          <DropdownMenuGroup>
            {options.map((option) => (
              <DropdownMenuCheckboxItem
                key={option.value}
                checked={value.includes(option.value)}
                closeOnClick={false}
                onCheckedChange={(isChecked) => toggle(option.value, isChecked)}
              >
                {option.label}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuGroup>
          {value.length === 0 ? null : (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => onChange([])}>{t("filters.reset")}</DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
      {current === undefined ? null : <ClearButton label={label} onClear={() => onChange([])} />}
    </div>
  )
}

interface DateRangeFilterProps {
  label: string
  value: IsoRange
  onChange: (value: IsoRange) => void
  /** Shortcuts for the next so many days from today, for dates that lie ahead. */
  nextDays?: readonly number[]
}

/** A from–to date range picked on a two-month calendar; either end may stay open. */
export function DateRangeFilter({ label, value, onChange, nextDays }: DateRangeFilterProps) {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const isOn = value.from !== undefined || value.to !== undefined
  const selected: DateRange | undefined = isOn
    ? { from: fromIso(value.from), to: fromIso(value.to) }
    : undefined
  const current = isOn ? `${show(value.from)} – ${show(value.to)}` : undefined
  // The first day picked opens a range up to today, which is what most searches want; a
  // second pick closes it there instead.
  const [isPickingEnd, setIsPickingEnd] = useState(false)
  const pick = (day: Date) => {
    const picked = format(day, ISO)
    if (isPickingEnd && value.from) {
      onChange(
        picked < value.from ? { from: picked, to: value.from } : { from: value.from, to: picked }
      )
      setIsPickingEnd(false)
      return
    }
    const today = todayIso()
    onChange(picked <= today ? { from: picked, to: today } : { from: today, to: picked })
    setIsPickingEnd(true)
  }
  const openChange = (next: boolean) => {
    setIsOpen(next)
    setIsPickingEnd(false)
  }
  return (
    <div className="flex items-center">
      <Popover open={isOpen} onOpenChange={openChange}>
        <PopoverTrigger render={<FilterButton label={label} current={current} />} />
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="range"
            numberOfMonths={2}
            captionLayout="dropdown"
            startMonth={START_MONTH}
            endMonth={END_MONTH}
            locale={dateLocale()}
            selected={selected}
            defaultMonth={selected?.from}
            onSelect={(_range, day) => pick(day)}
          />
          {nextDays?.length ? (
            <div className="flex flex-wrap gap-1 border-t p-2">
              {nextDays.map((days) => {
                const today = todayIso()
                const to = format(addDays(parseISO(today), days), ISO)
                const isPicked = value.from === today && value.to === to
                return (
                  <Button
                    key={days}
                    variant={isPicked ? "secondary" : "outline"}
                    size="sm"
                    aria-pressed={isPicked}
                    onClick={() => {
                      onChange({ from: today, to })
                      openChange(false)
                    }}
                  >
                    {t("filters.nextDays", { count: days })}
                  </Button>
                )
              })}
            </div>
          ) : null}
          <div className="flex justify-end gap-2 border-t p-2">
            <Button variant="ghost" size="sm" disabled={!isOn} onClick={() => onChange({})}>
              {t("filters.reset")}
            </Button>
            <Button size="sm" onClick={() => openChange(false)}>
              {t("filters.done")}
            </Button>
          </div>
        </PopoverContent>
      </Popover>
      {isOn ? <ClearButton label={label} onClear={() => onChange({})} /> : null}
    </div>
  )
}
