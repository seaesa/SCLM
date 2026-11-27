"use client"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

/** Value that stands for "no filter"; Base UI needs a non-null value to show a label. */
const ANY = "__any__"

interface ChoiceSelectProps<V extends string> {
  value: V | undefined
  onChange: (value: V | undefined) => void
  options: readonly { value: V; label: string }[]
  /** Label of the "no choice" entry; without it a choice is required. */
  anyLabel?: string
  /** Shown while nothing is chosen and there is no "no choice" entry. */
  placeholder?: string
  label: string
  className?: string
}

/** A dropdown filter: one of a fixed set of values, or (with `anyLabel`) none. */
export function ChoiceSelect<V extends string>({
  value,
  onChange,
  options,
  anyLabel,
  placeholder,
  label,
  className,
}: ChoiceSelectProps<V>) {
  const items = [...(anyLabel === undefined ? [] : [{ value: ANY, label: anyLabel }]), ...options]
  return (
    <Select
      items={items}
      value={value ?? (anyLabel === undefined ? null : ANY)}
      onValueChange={(next) => onChange(next === ANY || next === null ? undefined : (next as V))}
    >
      <SelectTrigger size="sm" aria-label={label} className={className}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {items.map((item) => (
          <SelectItem key={item.value} value={item.value}>
            {item.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
