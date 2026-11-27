"use client"

import {
  ArrowDown01Icon,
  ArrowRight01Icon,
  ArrowUpDownIcon,
  GridViewIcon,
} from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  columnVisibilityFeature,
  createExpandedRowModel,
  createSortedRowModel,
  FlexRender,
  rowExpandingFeature,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_basic,
  sortFn_datetime,
  sortFn_text,
  tableFeatures,
  useTable,
  type Column,
  type ColumnDef,
  type Row,
  type RowData,
} from "@tanstack/react-table"
import { Fragment } from "react"

import { useTranslation, type TranslationKey } from "@workspace/i18n"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

/** Features every list table has: sort the loaded rows, hide columns, expand a row. */
const dataTableFeatures = tableFeatures({
  rowSortingFeature,
  columnVisibilityFeature,
  rowExpandingFeature,
  sortedRowModel: createSortedRowModel(),
  expandedRowModel: createExpandedRowModel(),
  sortFns: {
    alphanumeric: sortFn_alphanumeric,
    basic: sortFn_basic,
    datetime: sortFn_datetime,
    text: sortFn_text,
  },
})

type Features = typeof dataTableFeatures
// oxlint-disable-next-line no-explicit-any -- column values differ per column; TanStack types them per column
type TableColumn<TData extends RowData> = ColumnDef<Features, TData, any>

/** A column with a stable id and the i18n key of its label; the table renders the header. */
export type DataColumn<TData extends RowData> = TableColumn<TData> & {
  id: string
  label: TranslationKey
}

export interface DataTableProps<TData extends RowData> {
  columns: DataColumn<TData>[]
  data: TData[]
  getRowId: (row: TData) => string
  /** Detail shown under a row when it is expanded; rows do not expand without it. */
  renderExpanded?: (row: TData) => React.ReactNode
  onRowClick?: (row: TData) => void
  /** Filters and actions left of the column picker. */
  toolbar?: React.ReactNode
  /** Under the table: usually the pager. */
  footer?: React.ReactNode
  /** Column ids hidden until the user shows them. */
  hiddenColumns?: readonly string[]
}

/** A list rendered as a table: sortable headers, a column picker and expandable rows. */
export function DataTable<TData extends RowData>({
  columns,
  data,
  getRowId,
  renderExpanded,
  onRowClick,
  toolbar,
  footer,
  hiddenColumns = NO_COLUMNS,
}: DataTableProps<TData>) {
  const { t } = useTranslation()
  const labels = new Map(columns.map((column) => [column.id, column.label]))
  const table = useTable({
    features: dataTableFeatures,
    columns: withHeaders(columns, Boolean(renderExpanded)),
    data,
    getRowId,
    getRowCanExpand: () => Boolean(renderExpanded),
    initialState: {
      columnVisibility: Object.fromEntries(hiddenColumns.map((id) => [id, false])),
    },
  })
  const rows = table.getRowModel().rows
  const columnCount = table.getVisibleLeafColumns().length

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-start gap-2">
        {toolbar}
        <DropdownMenu>
          <DropdownMenuTrigger render={<Button variant="outline" size="sm" className="ml-auto" />}>
            <HugeiconsIcon icon={GridViewIcon} data-icon="inline-start" />
            {t("table.columns")}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-48">
            <DropdownMenuGroup>
              <DropdownMenuLabel>{t("table.showColumns")}</DropdownMenuLabel>
              {table
                .getAllLeafColumns()
                .filter((column) => column.getCanHide())
                .map((column) => (
                  <DropdownMenuCheckboxItem
                    key={column.id}
                    checked={column.getIsVisible()}
                    onCheckedChange={(value) => column.toggleVisibility(value)}
                  >
                    {labels.has(column.id) ? t(labels.get(column.id) as TranslationKey) : column.id}
                  </DropdownMenuCheckboxItem>
                ))}
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <div className="overflow-hidden rounded-xl border">
        <Table>
          <TableHeader className="bg-muted/40">
            {table.getHeaderGroups().map((group) => (
              <TableRow key={group.id}>
                {group.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className={cn(header.column.id === "expand" && "w-10")}
                  >
                    {header.isPlaceholder ? null : <FlexRender header={header} />}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <Fragment key={row.id}>
                <TableRow
                  data-state={row.getIsExpanded() ? "selected" : undefined}
                  className={cn((onRowClick ?? renderExpanded) && "cursor-pointer")}
                  onClick={() => (onRowClick ? onRowClick(row.original) : row.toggleExpanded())}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="align-top">
                      <FlexRender cell={cell} />
                    </TableCell>
                  ))}
                </TableRow>
                {row.getIsExpanded() && renderExpanded ? (
                  <TableRow className="bg-muted/20 hover:bg-muted/20">
                    <TableCell colSpan={columnCount} className="p-0 whitespace-normal">
                      <div className="border-l-2 border-primary/60 px-6 py-4">
                        {renderExpanded(row.original)}
                      </div>
                    </TableCell>
                  </TableRow>
                ) : null}
              </Fragment>
            ))}
          </TableBody>
        </Table>
      </div>
      {footer ? <div className="flex justify-center">{footer}</div> : null}
    </div>
  )
}

const NO_COLUMNS: readonly string[] = []

function withHeaders<TData extends RowData>(
  columns: DataColumn<TData>[],
  canExpand: boolean
): TableColumn<TData>[] {
  const labelled = columns.map((column): TableColumn<TData> => ({
    ...column,
    header: ({ column: tableColumn }) => <ColumnHeader column={tableColumn} label={column.label} />,
  }))
  if (!canExpand) return labelled
  const expand: TableColumn<TData> = {
    id: "expand",
    enableHiding: false,
    enableSorting: false,
    header: () => null,
    cell: ({ row }) => <ExpandToggle row={row} />,
  }
  return [expand, ...labelled]
}

function ColumnHeader<TData extends RowData>({
  column,
  label,
}: {
  column: Column<Features, TData>
  label: TranslationKey
}) {
  const { t } = useTranslation()
  const text = t(label)
  return column.getCanSort() ? <SortableHeader column={column}>{text}</SortableHeader> : text
}

/** Translated text for a cell, so column definitions can stay outside components. */
export function Translated({ label }: { label: TranslationKey }) {
  const { t } = useTranslation()
  return t(label)
}

function ExpandToggle<TData extends RowData>({ row }: { row: Row<Features, TData> }) {
  const { t } = useTranslation()
  return (
    <Button
      variant="ghost"
      size="icon-sm"
      aria-expanded={row.getIsExpanded()}
      aria-label={row.getIsExpanded() ? t("table.collapse") : t("table.expand")}
      onClick={(event) => {
        event.stopPropagation()
        row.toggleExpanded()
      }}
    >
      <HugeiconsIcon icon={row.getIsExpanded() ? ArrowDown01Icon : ArrowRight01Icon} />
    </Button>
  )
}

/** A header that sorts the loaded rows when clicked. */
function SortableHeader<TData extends RowData>({
  column,
  children,
}: {
  column: Column<Features, TData>
  children: React.ReactNode
}) {
  const sorted = column.getIsSorted()
  return (
    <Button
      variant="ghost"
      size="sm"
      className="-ml-2 h-8 data-[sorted=true]:text-foreground"
      data-sorted={Boolean(sorted)}
      onClick={() => column.toggleSorting(sorted === "asc")}
    >
      {children}
      <HugeiconsIcon icon={ArrowUpDownIcon} data-icon="inline-end" className="opacity-60" />
    </Button>
  )
}
