import { AppSidebar } from "@/components/app-sidebar"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { TooltipProvider } from "@/components/ui/tooltip"
import { AuthGate } from "@/features/auth/components/auth-gate"
import { SidebarUser } from "@/features/auth/components/sidebar-user"
import { UnverifiedBanner } from "@/features/auth/components/unverified-banner"

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate require="auth">
      <TooltipProvider>
        <SidebarProvider>
          <AppSidebar footer={<SidebarUser />} />
          <SidebarInset className="min-w-0">
            <UnverifiedBanner />
            {children}
          </SidebarInset>
        </SidebarProvider>
      </TooltipProvider>
    </AuthGate>
  )
}
