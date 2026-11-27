"use client"

import { THEME_MODES, usePreferencesStore } from "@workspace/core/preferences"
import { useTranslation } from "@workspace/i18n"

import {
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from "@/components/ui/dropdown-menu"

/** Theme radio group, rendered inside any DropdownMenuContent. */
export function PreferencesMenuItems() {
  const { t } = useTranslation()
  const { theme, setTheme } = usePreferencesStore()

  return (
    <DropdownMenuGroup>
      <DropdownMenuLabel>{t("settings.theme")}</DropdownMenuLabel>
      <DropdownMenuRadioGroup value={theme} onValueChange={(v) => setTheme(v as typeof theme)}>
        {THEME_MODES.map((mode) => (
          <DropdownMenuRadioItem key={mode} value={mode}>
            {t(`settings.themes.${mode}`)}
          </DropdownMenuRadioItem>
        ))}
      </DropdownMenuRadioGroup>
    </DropdownMenuGroup>
  )
}
