/** Web-only constants. Shared tunables live in `@workspace/core` config; env in `lib/env.ts`. */

/** Locale cookie, read by the server (i18n-server.ts) and written by PreferencesSync. */
export const LOCALE_COOKIE = "locale"
export const LOCALE_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365

/** Prices (tables, fuel clauses, fuel prices) are hidden until they are ready to be shown; the
 * data and the API stay as they are. Turn on to show them again. */
export const IS_PRICING_VISIBLE = false

/** The dashboard is hidden for now: the home page opens the contract list instead. */
export const IS_OVERVIEW_VISIBLE = false

/** Adding contracts and documents (including re-signing) is hidden for now; the archive is
 * read and its facts corrected only. */
export const CAN_ADD_DOCUMENTS = false
