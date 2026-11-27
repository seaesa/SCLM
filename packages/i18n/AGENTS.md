# packages/i18n — user-visible text for web and mobile (Vietnamese)

- The product ships in Vietnamese only, but every string still goes through i18n: `src/locales/vi.ts`
  is the reference shape (`Messages`), so components never hold literal copy and a second language
  can be added later without touching them.
- `errors` is typed `Record<ClientErrorCode, string>` (backend `ErrorCode` enum + client codes):
  after a backend adds a code and `pnpm codegen` runs, typecheck fails until it is translated here.
- `validation.<pydanticType>` translates server-side 422 field errors (`string_too_short`, …),
  interpolated with the error `params` (`{{min_length}}`).
- Keys are grouped by feature (`auth`, `partners`, `contracts`, `profile`, `device`) + shared (`common`, `settings`,
  `validation`, `errors`). Interpolation `{{name}}`, plurals `key_one` / `key_other`.
- `i18n` is a single, synchronously initialised instance (resources bundled). Language is driven by
  the preferences store in `@workspace/core` — never call `i18n.changeLanguage` from apps; use
  `usePreferencesStore().setLocale`. Server code (Next metadata) uses `i18n.getFixedT(locale)`.
- In components: `const { t } = useTranslation()` from `@workspace/i18n`. Messages that may be keys
  or plain text (form errors) render through `translateMessage()`.
- Adding a language: add it to `SUPPORTED_LOCALES`, create `locales/<lng>.ts`, map a date-fns locale
  in `packages/core/src/lib/date.ts` and a Zod locale in `features/preferences/store.ts`.
