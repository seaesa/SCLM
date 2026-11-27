import Image from "next/image"

import { SettingsButton } from "@/features/preferences/components/settings-button"

/** Centered shell shared by every auth screen (guest pages and the verify page). */
export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="relative flex min-h-svh items-center justify-center bg-muted/40 p-6">
      <div className="absolute top-4 right-4">
        <SettingsButton />
      </div>
      <div className="flex w-full max-w-sm flex-col gap-6">
        {/* The wordmark is navy on transparent: a white plate keeps it legible in dark mode. */}
        <Image
          src="/brand/wordmark.png"
          alt="SPIDER Contract Lifecycle Management"
          width={960}
          height={294}
          priority
          className="mx-auto h-auto w-64 dark:rounded-xl dark:bg-white dark:p-3"
        />
        {children}
      </div>
    </main>
  )
}
