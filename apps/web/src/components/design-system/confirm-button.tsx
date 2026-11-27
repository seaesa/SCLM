"use client"

import { useState, type ReactNode } from "react"

import { useTranslation } from "@workspace/i18n"

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"

interface ConfirmButtonProps {
  trigger: ReactNode
  title: string
  description: string
  confirmLabel: string
  onConfirm: () => Promise<unknown>
  children?: ReactNode
  canConfirm?: boolean
  /** `destructive` for removals, `default` for actions that create something. */
  variant?: "destructive" | "default"
}

/** An action behind a confirmation; stays open while it runs. */
export function ConfirmButton({
  trigger,
  title,
  description,
  confirmLabel,
  onConfirm,
  children,
  canConfirm = true,
  variant = "destructive",
}: ConfirmButtonProps) {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const confirm = async () => {
    setIsRunning(true)
    try {
      await onConfirm()
      setIsOpen(false)
    } catch {
      // The action has already told the user why it failed; stay open so they can go back.
    } finally {
      setIsRunning(false)
    }
  }
  return (
    <AlertDialog open={isOpen} onOpenChange={setIsOpen}>
      <AlertDialogTrigger render={<Button variant="outline" size="sm" />}>
        {trigger}
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        {children}
        <AlertDialogFooter>
          <AlertDialogCancel>{t("contracts.remove.back")}</AlertDialogCancel>
          <Button
            variant={variant}
            disabled={isRunning || !canConfirm}
            onClick={() => void confirm()}
          >
            {confirmLabel}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
