import type { vi } from "./locales/vi"

/** Same keys as `vi`, any string values. */
type DeepStrings<T> = { [K in keyof T]: T[K] extends string ? string : DeepStrings<T[K]> }

export type Messages = DeepStrings<typeof vi>
