"use client"

import { ArrowLeft01Icon, ArrowRight01Icon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"

import { formatNumber } from "@workspace/core/lib/number"
import { PAGE_SIZE_OPTIONS, pageCount, type Paging } from "@workspace/core/lib/paging"
import { useTranslation } from "@workspace/i18n"

import { ChoiceSelect } from "@/components/design-system/choice-select"
import { Button } from "@/components/ui/button"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
} from "@/components/ui/pagination"

/** Page numbers to show: the first, the last, and two either side of the current one. */
function visiblePages(current: number, last: number): (number | "gap")[] {
  const pages: (number | "gap")[] = []
  for (let page = 1; page <= last; page += 1) {
    const isNear = Math.abs(page - current) <= 2
    if (page === 1 || page === last || isNear) pages.push(page)
    else if (pages.at(-1) !== "gap") pages.push("gap")
  }
  return pages
}

interface ListPaginationProps {
  total: number
  paging: Paging
  /** Shown instead of the pager when nothing matches. */
  emptyText?: string
}

/** "21–40 of 958", page links and rows per page, under a list. */
export function ListPagination({ total, paging, emptyText }: ListPaginationProps) {
  const { t } = useTranslation()
  if (total === 0) {
    return <p className="py-6 text-sm text-muted-foreground">{emptyText ?? t("list.empty")}</p>
  }
  const { page, pageSize, setPage, setPageSize } = paging
  const last = pageCount(total, pageSize)
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(total, page * pageSize)
  const sizes = PAGE_SIZE_OPTIONS.map((size) => ({ value: String(size), label: String(size) }))
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
      <p className="text-muted-foreground tabular-nums">
        {t("list.range", {
          from: formatNumber(from),
          to: formatNumber(to),
          total: formatNumber(total),
        })}
      </p>
      <Pagination className="mx-0 w-auto">
        <PaginationContent>
          <PaginationItem>
            <Button
              variant="ghost"
              size="icon"
              aria-label={t("list.previousPage")}
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              <HugeiconsIcon icon={ArrowLeft01Icon} strokeWidth={2} />
            </Button>
          </PaginationItem>
          {visiblePages(page, last).map((item, index) =>
            item === "gap" ? (
              // Gaps have no identity of their own; their position is stable for one render.
              // oxlint-disable-next-line react/no-array-index-key -- see above
              <PaginationItem key={`gap-${index}`}>
                <PaginationEllipsis />
              </PaginationItem>
            ) : (
              <PaginationItem key={item}>
                <Button
                  variant={item === page ? "outline" : "ghost"}
                  size="icon"
                  aria-current={item === page ? "page" : undefined}
                  onClick={() => setPage(item)}
                  className="tabular-nums"
                >
                  {item}
                </Button>
              </PaginationItem>
            )
          )}
          <PaginationItem>
            <Button
              variant="ghost"
              size="icon"
              aria-label={t("list.nextPage")}
              disabled={page >= last}
              onClick={() => setPage(page + 1)}
            >
              <HugeiconsIcon icon={ArrowRight01Icon} strokeWidth={2} />
            </Button>
          </PaginationItem>
        </PaginationContent>
      </Pagination>
      <div className="flex items-center gap-2 text-muted-foreground">
        <span>{t("list.rowsPerPage")}</span>
        <ChoiceSelect
          label={t("list.rowsPerPage")}
          value={String(pageSize)}
          onChange={(size) => setPageSize(Number(size ?? PAGE_SIZE_OPTIONS[0]))}
          options={sizes}
        />
      </div>
    </div>
  )
}
