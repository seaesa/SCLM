import type { RowData } from "@tanstack/react-table"

import type { PriceLineRead } from "@workspace/api-client"

import type { DataColumn } from "@/components/design-system/data-table/data-table"

import { formatAmount } from "./pricing-format"

const text = (value: string | null) => value ?? "—"

/** The printed columns of a price line, shared by the table card, the lookup and the proposal. */
export function priceLineColumns<T extends RowData>(
  lineOf: (row: T) => PriceLineRead
): DataColumn<T>[] {
  return [
    {
      id: "service",
      label: "pricing.columns.service",
      accessorFn: (row) => lineOf(row).service,
    },
    {
      id: "origin",
      label: "pricing.columns.origin",
      accessorFn: (row) => lineOf(row).origin ?? "",
      cell: ({ row }) => text(lineOf(row.original).origin),
    },
    {
      id: "destination",
      label: "pricing.columns.destination",
      accessorFn: (row) => lineOf(row).destination ?? "",
      cell: ({ row }) => text(lineOf(row.original).destination),
    },
    {
      id: "vehicle",
      label: "pricing.columns.vehicle",
      accessorFn: (row) => lineOf(row).vehicle ?? "",
      cell: ({ row }) => text(lineOf(row.original).vehicle),
    },
    {
      id: "unitPrice",
      label: "pricing.columns.unitPrice",
      accessorFn: (row) => Number(lineOf(row).unitPrice),
      cell: ({ row }) => (
        <span className="font-medium tabular-nums">
          {formatAmount(lineOf(row.original).unitPrice)}
        </span>
      ),
    },
    {
      id: "unit",
      label: "pricing.columns.unit",
      accessorFn: (row) => lineOf(row).unit,
    },
    {
      id: "note",
      label: "pricing.columns.note",
      accessorFn: (row) => lineOf(row).note ?? "",
      cell: ({ row }) => (
        <span className="line-clamp-2 max-w-56">{text(lineOf(row.original).note)}</span>
      ),
    },
  ]
}
