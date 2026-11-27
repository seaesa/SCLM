import { HugeiconsIcon, type IconSvgElement } from "@hugeicons/react"

import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

/** An icon button of a file viewer's toolbar, named by its tooltip. */
export function ToolButton({
  icon,
  label,
  isActive,
  ...props
}: {
  icon: IconSvgElement
  label: string
  isActive?: boolean
} & React.ComponentProps<typeof Button>) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            variant={isActive ? "secondary" : "ghost"}
            size="icon-sm"
            aria-label={label}
            {...props}
          />
        }
      >
        <HugeiconsIcon icon={icon} />
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}
