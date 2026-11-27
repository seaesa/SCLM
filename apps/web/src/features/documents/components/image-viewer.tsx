"use client"

import { RotateClockwiseIcon, ZoomInAreaIcon, ZoomOutAreaIcon } from "@hugeicons/core-free-icons"
import { useState } from "react"

import { useTranslation } from "@workspace/i18n"

import { Button } from "@/components/ui/button"
import { FileFrame, FileMessage } from "@/features/documents/components/file-frame"
import { ToolButton } from "@/features/documents/components/tool-button"

const ZOOM_STEPS = [0.5, 0.75, 1, 1.5, 2, 3] as const

interface ImageViewerProps {
  url: string
  fileName: string
  className?: string
}

/** A scanned page or photo: fit to the frame, or zoomed and turned. */
export function ImageViewer({ url, fileName, className }: ImageViewerProps) {
  const { t } = useTranslation()
  const [zoom, setZoom] = useState<number | "fit">("fit")
  const [rotation, setRotation] = useState(0)
  const [isBroken, setIsBroken] = useState(false)
  const zoomBy = (direction: 1 | -1) => {
    const scale = zoom === "fit" ? 1 : zoom
    const index = ZOOM_STEPS.findIndex((step) => step >= scale)
    setZoom(ZOOM_STEPS[Math.min(Math.max(0, index + direction), ZOOM_STEPS.length - 1)] ?? 1)
  }

  return (
    <FileFrame
      url={url}
      fileName={fileName}
      className={className}
      tools={
        <>
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
        </>
      }
    >
      {isBroken ? (
        <FileMessage>{t("pdf.loadError")}</FileMessage>
      ) : (
        <div className="min-h-0 flex-1 overflow-auto p-4">
          {/* A signed link to a private file: next/image would fetch it again on the server. */}
          {/* oxlint-disable-next-line nextjs/no-img-element */}
          <img
            src={url}
            alt={fileName}
            onError={() => setIsBroken(true)}
            style={{
              rotate: `${rotation}deg`,
              width: zoom === "fit" ? undefined : `${zoom * 100}%`,
            }}
            className={
              zoom === "fit"
                ? "mx-auto max-h-full max-w-full object-contain shadow-md"
                : "mx-auto max-w-none shadow-md"
            }
          />
        </div>
      )}
    </FileFrame>
  )
}
