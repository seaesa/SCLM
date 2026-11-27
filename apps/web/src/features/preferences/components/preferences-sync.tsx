"use client"

import { useTheme } from "next-themes"
import { useEffect, useEffectEvent } from "react"

import { useLocale, usePreferencesStore } from "@workspace/core/preferences"

import { LOCALE_COOKIE, LOCALE_COOKIE_MAX_AGE_SECONDS } from "@/config"

/** Applies shared preferences to web-only mechanisms: next-themes, <html lang>, locale cookie. */
export function PreferencesSync() {
  const theme = usePreferencesStore((s) => s.theme)
  const locale = useLocale()
  const { setTheme } = useTheme()

  // next-themes hands out a new setTheme whenever its theme changes (another tab, the system):
  // depending on it would push this tab's preference back over that change. Apply only when the
  // preference itself changes.
  const applyTheme = useEffectEvent((next: typeof theme) => setTheme(next))
  useEffect(() => applyTheme(theme), [theme])

  // The preference store is not shared between tabs on its own; follow a change made elsewhere.
  useEffect(() => {
    function onStorage(event: StorageEvent) {
      if (event.key === usePreferencesStore.persist.getOptions().name) {
        void usePreferencesStore.persist.rehydrate()
      }
    }
    window.addEventListener("storage", onStorage)
    return () => window.removeEventListener("storage", onStorage)
  }, [])

  useEffect(() => {
    document.documentElement.lang = locale
    document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=${LOCALE_COOKIE_MAX_AGE_SECONDS}; samesite=lax`
  }, [locale])

  return null
}
