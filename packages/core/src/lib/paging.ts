import { useState } from "react"
import type { ZodType } from "zod"

import { PAGE_SIZE_OPTIONS } from "../config"

export { PAGE_SIZE_OPTIONS }

export interface NumberedPage<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

/** Page number and size of one list. Call `resetPage` whenever a filter changes, so a narrower
 * result is not opened on a page past its end. */
export function usePaging(initialSize: number = PAGE_SIZE_OPTIONS[0]) {
  const [page, setPage] = useState(1)
  const [pageSize, setSize] = useState(initialSize)
  return {
    page,
    pageSize,
    setPage,
    setPageSize: (size: number) => {
      setSize(size)
      setPage(1)
    },
    resetPage: () => setPage(1),
  }
}

export type Paging = ReturnType<typeof usePaging>

export function pageCount(total: number, pageSize: number): number {
  return Math.max(1, Math.ceil(total / pageSize))
}

/** The trimmed search text when the API accepts it (its generated rule), else no filter:
 * typing one character lists everything instead of failing the request. */
export function searchTerm(rule: ZodType, text: string): string | undefined {
  const trimmed = text.trim()
  return trimmed && rule.safeParse(trimmed).success ? trimmed : undefined
}
