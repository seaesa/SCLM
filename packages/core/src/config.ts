/**
 * Client-side tunables shared by web and mobile. Values owned by the backend (page sizes,
 * transport paths, validation limits) come from the generated contract instead, never from here.
 */

/** React Query: how long fetched data counts as fresh before a background refetch. */
export const QUERY_STALE_TIME_MS = 30_000
/** React Query: retries for network / 5xx failures (4xx are never retried). */
export const QUERY_MAX_RETRIES = 2

/** Keys of persisted stores. Changing one logs every user out / resets their preferences. */
export const STORAGE_KEYS = {
  auth: "auth",
  preferences: "preferences",
} as const

/** Rows per page a user can choose in a list; the first is the default. The API caps it at 100. */
export const PAGE_SIZE_OPTIONS = [20, 50, 100] as const
