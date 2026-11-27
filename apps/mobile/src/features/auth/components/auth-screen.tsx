import { KeyboardAvoidingView, Platform, ScrollView, View } from "react-native"

import { useTranslation } from "@workspace/i18n"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

import { LoginForm } from "./login-form"

/** Sign-in shell. */
export function AuthScreen() {
  const { t } = useTranslation()
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      className="bg-background flex-1"
    >
      <ScrollView
        contentContainerClassName="flex-grow justify-center gap-6 p-6"
        keyboardShouldPersistTaps="handled"
      >
        <View className="mx-auto w-full max-w-sm gap-6">
          <Card>
            <CardHeader>
              <CardTitle>{t("auth.login.title")}</CardTitle>
              <CardDescription>{t("auth.login.description")}</CardDescription>
            </CardHeader>
            <CardContent>
              <LoginForm />
            </CardContent>
          </Card>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}
