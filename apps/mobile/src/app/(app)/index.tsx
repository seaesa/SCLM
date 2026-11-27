import { SafeAreaView } from "react-native-safe-area-context"

import { useTranslation } from "@workspace/i18n"

import { Text } from "@/components/ui/text"
import { UnverifiedBanner } from "@/features/auth/components/unverified-banner"

export default function HomeScreen() {
  const { t } = useTranslation()
  return (
    <SafeAreaView edges={["top"]} className="bg-background flex-1">
      <Text variant="h3" className="px-4 pt-4">
        {t("home.title")}
      </Text>
      <UnverifiedBanner />
      <Text className="text-muted-foreground px-4 pt-2">{t("home.webOnly")}</Text>
    </SafeAreaView>
  )
}
