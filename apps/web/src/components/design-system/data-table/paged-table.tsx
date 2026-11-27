"use client"

import type { RowData } from "@tanstack/react-table"

import type { Paging } from "@workspace/core/lib/paging"

import { ListStates } from "../list-states"
import { ListPagination } from "../pagination"
import { DataTable, type DataTableProps } from "./data-table"

interface PagedQuery<TData> {
  isPending: boolean
  isError: boolean
  data?: { items: TData[]; total: number }
  refetch: () => unknown
}

interface PagedTableProps<TData extends RowData> extends Omit<
  DataTableProps<TData>,
  "data" | "footer"
> {
  query: PagedQuery<TData>
  paging: Paging
  /** Shown under the table instead of the page range when nothing matches. */
  emptyText?: string
}

/** One page of a server list: loading and error states, the table, then the pager. */
export function PagedTable<TData extends RowData>({
  query,
  paging,
  emptyText,
  ...table
}: PagedTableProps<TData>) {
  return (
    <ListStates
      isPending={query.isPending}
      isError={query.isError}
      isEmpty={false}
      onRetry={() => void query.refetch()}
    >
      <DataTable
        {...table}
        data={query.data?.items ?? []}
        footer={
          <ListPagination total={query.data?.total ?? 0} paging={paging} emptyText={emptyText} />
        }
      />
    </ListStates>
  )
}
