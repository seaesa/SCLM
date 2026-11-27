import type { Metadata } from "next"

import { FuelPriceList } from "@/features/pricing/components/fuel-price-list"
import { getServerT } from "@/lib/i18n-server"

export async function generateMetadata(): Promise<Metadata> {
  const t = await getServerT()
  return { title: t("pricing.fuelPrices.title") }
}

export default function FuelPricesPage() {
  return <FuelPriceList />
}
