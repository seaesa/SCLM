"use client"

import { Calendar03Icon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { format, isValid, parse, parseISO } from "date-fns"
import { useState } from "react"

import { dateLocale } from "@workspace/core/lib/date"
import { useTranslation } from "@workspace/i18n"

import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

const ISO = "yyyy-MM-dd"
// Dates are read off Vietnamese documents, so they are typed and shown day first whatever the
// interface language: "03/04/2025" is always 3 April, never March 4.
const DISPLAY = "dd/MM/yyyy"
const TYPED_FORMATS = ["d/M/yyyy", "d-M-yyyy", "d.M.yyyy", "d/M/yy", ISO]
// Contracts in the archive start in the 2010s; renewals run a decade ahead.
const START_MONTH = new Date(2005, 0)
const END_MONTH = new Date(new Date().getFullYear() + 15, 11)

const toIso = (date: Date) => format(date, ISO)
const fromIso = (value: string | null | undefined) => {
  const date = value ? parseISO(value) : undefined
  return date && isValid(date) ? date : undefined
}
const display = (date: Date | undefined) => (date ? format(date, DISPLAY) : "")
const parseTyped = (raw: string) =>
  TYPED_FORMATS.map((pattern) => parse(raw, pattern, new Date())).find(
    (date) => isValid(date) && date.getFullYear() >= 1900
  )

interface DatePickerProps {
  /** ISO date (yyyy-MM-dd) or null. */
  value: string | null | undefined
  onChange: (value: string | null) => void
  id?: string
  disabled?: boolean
  "aria-invalid"?: boolean
}

/**
 * A date typed in the local short format (31/12/2026) or picked from a calendar with month and
 * year dropdowns, so entering a date read off a scan does not need dozens of clicks.
 */
export function DatePicker({ value, onChange, id, disabled, ...aria }: DatePickerProps) {
  const { t } = useTranslation()
  const selected = fromIso(value)
  const [text, setText] = useState(() => display(selected))
  const [isUnreadable, setIsUnreadable] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const [lastValue, setLastValue] = useState(value)
  if (value !== lastValue) {
    setLastValue(value)
    setText(display(fromIso(value)))
    setIsUnreadable(false)
  }

  const commit = (raw: string) => {
    if (!raw.trim()) {
      setIsUnreadable(false)
      onChange(null)
      return
    }
    const parsed = parseTyped(raw.trim())
    // An unreadable entry stays visible and marked, instead of silently reverting.
    setIsUnreadable(!parsed)
    // An unreadable entry is not a clear: the last good date stays until it is fixed.
    if (parsed) {
      setText(display(parsed))
      onChange(toIso(parsed))
    }
  }

  return (
    <InputGroup>
      <InputGroupInput
        id={id}
        value={text}
        disabled={disabled}
        placeholder={t("date.placeholder")}
        inputMode="numeric"
        onChange={(event) => setText(event.target.value)}
        onBlur={(event) => commit(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault()
            commit(event.currentTarget.value)
          }
        }}
        {...aria}
        aria-invalid={isUnreadable || aria["aria-invalid"]}
      />
      <InputGroupAddon align="inline-end">
        <Popover open={isOpen} onOpenChange={setIsOpen}>
          <PopoverTrigger
            render={
              <InputGroupButton size="icon-xs" disabled={disabled} aria-label={t("date.open")} />
            }
          >
            <HugeiconsIcon icon={Calendar03Icon} />
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="end">
            <Calendar
              mode="single"
              captionLayout="dropdown"
              startMonth={START_MONTH}
              endMonth={END_MONTH}
              locale={dateLocale()}
              selected={selected}
              defaultMonth={selected}
              onSelect={(date) => {
                onChange(date ? toIso(date) : null)
                setIsOpen(false)
              }}
            />
            <div className="flex justify-between border-t p-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  onChange(toIso(new Date()))
                  setIsOpen(false)
                }}
              >
                {t("date.today")}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  onChange(null)
                  setIsOpen(false)
                }}
              >
                {t("date.clear")}
              </Button>
            </div>
          </PopoverContent>
        </Popover>
      </InputGroupAddon>
    </InputGroup>
  )
}
