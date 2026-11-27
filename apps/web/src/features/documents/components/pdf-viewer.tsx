"use client"

import "react-pdf/dist/Page/AnnotationLayer.css"
import "react-pdf/dist/Page/TextLayer.css"

import {
  ArrowLeft01Icon,
  ArrowRight01Icon,
  Download01Icon,
  FullScreenIcon,
  LayoutLeftIcon,
  LinkSquare02Icon,
  RotateClockwiseIcon,
  ZoomInAreaIcon,
  ZoomOutAreaIcon,
} from "@hugeicons/core-free-icons"
import { useEffect, useRef, useState } from "react"
import { Document, Page, pdfjs, Thumbnail } from "react-pdf"

import { useTranslation } from "@workspace/i18n"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { ToolButton } from "@/features/documents/components/tool-button"
import { cn } from "@/lib/utils"

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString()

// The download link expires after a few minutes, so the whole file is read in one request
// instead of ranges fetched later as pages are turned.
const DOCUMENT_OPTIONS = { disableRange: true }
const ZOOM_STEPS = [0.5, 0.75, 1, 1.25, 1.5, 2, 3] as const
const THUMBNAIL_WIDTH = 96

export interface PdfViewerProps {
  url: string
  fileName: string
  /** Page to show (1-based); the viewer follows it whenever it changes, e.g. a cited page. */
  page?: number
  onPageChange?: (page: number) => void
  className?: string
}

/** A full PDF reader: thumbnails, paging, zoom to fit or by step, rotation and full screen. */
export function PdfViewer({ url, fileName, page, onPageChange, className }: PdfViewerProps) {
  const { t } = useTranslation()
  const frame = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLDivElement>(null)
  const [pageCount, setPageCount] = useState(0)
  const [current, setCurrent] = useState(page ?? 1)
  const [requested, setRequested] = useState(page)
  const [zoom, setZoom] = useState<number | "fit">("fit")
  const [rotation, setRotation] = useState(0)
  // A scan often stores its orientation in the PDF (/Rotate); `rotate` replaces it, so add to it.
  const [ownRotation, setOwnRotation] = useState(0)
  const [hasThumbnails, setHasThumbnails] = useState(true)
  const [width, setWidth] = useState(0)
  const [pageInput, setPageInput] = useState(String(page ?? 1))

  if (page !== requested) {
    setRequested(page)
    if (page) {
      setCurrent(page)
      setPageInput(String(page))
    }
  }

  useEffect(() => {
    const element = canvas.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => setWidth(entry?.contentRect.width ?? 0))
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  const goTo = (target: number) => {
    const next = Math.min(Math.max(1, target), pageCount || 1)
    setCurrent(next)
    setPageInput(String(next))
    onPageChange?.(next)
  }
  // Arrow keys turn pages while focus is anywhere in the viewer except the page box.
  useEffect(() => {
    const element = frame.current
    if (!element) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement) return
      if (event.key === "ArrowRight" || event.key === "PageDown") goTo(current + 1)
      if (event.key === "ArrowLeft" || event.key === "PageUp") goTo(current - 1)
    }
    element.addEventListener("keydown", onKeyDown)
    return () => element.removeEventListener("keydown", onKeyDown)
  })
  const zoomBy = (direction: 1 | -1) => {
    const scale = zoom === "fit" ? 1 : zoom
    const index = ZOOM_STEPS.findIndex((step) => step >= scale)
    const next = ZOOM_STEPS[Math.min(Math.max(0, index + direction), ZOOM_STEPS.length - 1)]
    setZoom(next ?? 1)
  }
  const pageWidth = Math.max(200, width - 32)

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
      <div className="flex flex-wrap items-center gap-1 border-b bg-background px-2 py-1.5">
        <ToolButton
          icon={LayoutLeftIcon}
          label={t("pdf.thumbnails")}
          isActive={hasThumbnails}
          onClick={() => setHasThumbnails((value) => !value)}
        />
        <ToolButton
          icon={ArrowLeft01Icon}
          label={t("pdf.previous")}
          disabled={current <= 1}
          onClick={() => goTo(current - 1)}
        />
        <form
          className="flex items-center gap-1 text-sm"
          onSubmit={(event) => {
            event.preventDefault()
            goTo(Number(pageInput) || current)
          }}
        >
          <Input
            value={pageInput}
            onChange={(event) => setPageInput(event.target.value)}
            onBlur={() => goTo(Number(pageInput) || current)}
            inputMode="numeric"
            aria-label={t("pdf.page")}
            className="h-7 w-12 px-1 text-center"
          />
          <span className="text-muted-foreground">/ {pageCount || "–"}</span>
        </form>
        <ToolButton
          icon={ArrowRight01Icon}
          label={t("pdf.next")}
          disabled={current >= pageCount}
          onClick={() => goTo(current + 1)}
        />
        <span className="mx-1 h-5 w-px bg-border" />
        <ToolButton icon={ZoomOutAreaIcon} label={t("pdf.zoomOut")} onClick={() => zoomBy(-1)} />
        <Button
          variant={zoom === "fit" ? "secondary" : "ghost"}
          size="sm"
          className="h-7 min-w-14 px-2 tabular-nums"
          onClick={() => setZoom(zoom === "fit" ? 1 : "fit")}
        >
          {zoom === "fit" ? t("pdf.fitWidth") : `${Math.round(zoom * 100)}%`}
        </Button>
        <ToolButton icon={ZoomInAreaIcon} label={t("pdf.zoomIn")} onClick={() => zoomBy(1)} />
        <ToolButton
          icon={RotateClockwiseIcon}
          label={t("pdf.rotate")}
          onClick={() => setRotation((value) => (value + 90) % 360)}
        />
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
      <Document
        file={url}
        options={DOCUMENT_OPTIONS}
        onLoadSuccess={({ numPages }) => {
          setPageCount(numPages)
          if (current > numPages) goTo(1)
        }}
        loading={<Skeleton className="m-4 h-[60vh] flex-1" />}
        error={<p className="p-6 text-sm text-destructive">{t("pdf.loadError")}</p>}
        className="flex min-h-0 flex-1"
      >
        {hasThumbnails && pageCount > 0 ? (
          <div className="flex w-32 shrink-0 flex-col items-center gap-3 overflow-y-auto border-r bg-background/60 py-3">
            {Array.from({ length: pageCount }, (_, index) => (
              <LazyThumbnail
                key={index}
                pageNumber={index + 1}
                isCurrent={current === index + 1}
                onSelect={goTo}
              />
            ))}
          </div>
        ) : null}
        <div ref={canvas} className="min-w-0 flex-1 overflow-auto p-4">
          <Page
            pageNumber={current}
            rotate={(ownRotation + rotation) % 360}
            onLoadSuccess={(loaded) => setOwnRotation(loaded.rotate)}
            width={zoom === "fit" ? pageWidth : undefined}
            scale={zoom === "fit" ? 1 : zoom}
            className="mx-auto w-fit shadow-md"
            loading={<Skeleton className="mx-auto h-[60vh] w-full max-w-3xl" />}
          />
        </div>
      </Document>
    </div>
  )
}

/** A page thumbnail drawn only once it scrolls into view: a contract can run to 300 pages. */
function LazyThumbnail({
  pageNumber,
  isCurrent,
  onSelect,
}: {
  pageNumber: number
  isCurrent: boolean
  onSelect: (page: number) => void
}) {
  const ref = useRef<HTMLButtonElement>(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element || isVisible) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) setIsVisible(true)
      },
      { rootMargin: "400px" }
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [isVisible])

  useEffect(() => {
    if (isCurrent) ref.current?.scrollIntoView({ block: "nearest" })
  }, [isCurrent])

  return (
    <button
      ref={ref}
      type="button"
      onClick={() => onSelect(pageNumber)}
      className={cn(
        "flex flex-col items-center gap-1 rounded-md p-1 text-xs text-muted-foreground",
        isCurrent && "bg-primary/10 text-foreground ring-2 ring-primary"
      )}
    >
      {isVisible ? (
        <Thumbnail pageNumber={pageNumber} width={THUMBNAIL_WIDTH} className="shadow-sm" />
      ) : (
        <span className="block h-32 w-24 rounded-sm bg-muted" />
      )}
      {pageNumber}
    </button>
  )
}
