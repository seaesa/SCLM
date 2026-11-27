import { Skeleton } from "@/components/ui/skeleton"
import { getServerT } from "@/lib/i18n-server"

/** Shown while an `(app)` route's data is still streaming in. */
export default async function AppLoading() {
  const t = await getServerT()

  return (
    <div className="flex flex-col gap-4">
      <span role="status" className="sr-only">
        {t("common.loading")}
      </span>
      {Array.from({ length: 4 }, (_, index) => (
        <Skeleton key={index} className="h-12 w-full" />
      ))}
    </div>
  )
}
