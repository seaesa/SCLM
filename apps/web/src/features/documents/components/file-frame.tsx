"use client"

import { Download01Icon, FullScreenIcon, LinkSquare02Icon } from "@hugeicons/core-free-icons"
import { useQuery } from "@tanstack/react-query"
import { useRef } from "react"

import { useTranslation } from "@workspace/i18n"

import { ToolButton } from "@/features/documents/components/tool-button"
import { cn } from "@/lib/utils"

interface FileFrameProps {
  url: string
  fileName: string
  /** The viewer's own tools, shown before full screen, open and download. */
  tools?: React.ReactNode
  className?: string
  children: React.ReactNode
}

/** The frame every file viewer shares: its tools on top, the file below. */
export function FileFrame({ url, fileName, tools, className, children }: FileFrameProps) {
  const { t } = useTranslation()
  const frame = useRef<HTMLDivElement>(null)
  return (
    <div
      ref={frame}
      className={cn(
        "flex h-full min-h-[60vh] flex-col overflow-hidden rounded-xl border bg-muted/30",
        className
      )}
      role="region"
      aria-label={fileName}
      tabIndex={-1}
    >
      <div className="flex min-h-11 flex-wrap items-center gap-1 border-b bg-background px-2 py-1.5">
        {tools}
        <div className="ml-auto flex items-center gap-1">
          <ToolButton
            icon={FullScreenIcon}
            label={t("pdf.fullScreen")}
            onClick={() => void frame.current?.requestFullscreen()}
          />
          <ToolButton
            icon={LinkSquare02Icon}
            label={t("pdf.openNewTab")}
            nativeButton={false}
            render={
              <a href={url} target="_blank" rel="noreferrer" aria-label={t("pdf.openNewTab")} />
            }
          />
          <ToolButton
            icon={Download01Icon}
            label={t("pdf.download")}
            nativeButton={false}
            render={<a href={url} download={fileName} aria-label={t("pdf.download")} />}
          />
        </div>
      </div>
      <div className="flex min-h-0 flex-1 flex-col">{children}</div>
    </div>
  )
}

/** A message in place of the file, e.g. when it cannot be shown here. */
export function FileMessage({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
      {children}
    </div>
  )
}

/** The whole file, for a viewer that parses it itself. */
export async function fetchBytes(url: string, signal?: AbortSignal): Promise<ArrayBuffer> {
  const response = await fetch(url, { signal })
  if (!response.ok) throw new Error(`${response.status}`)
  return response.arrayBuffer()
}

/** The file's bytes, read once per link. */
export function useFileBytes(url: string) {
  return useQuery({
    queryKey: ["file-bytes", url],
    queryFn: ({ signal }) => fetchBytes(url, signal),
    staleTime: Infinity,
    gcTime: 60_000,
    retry: 1,
  })
}
