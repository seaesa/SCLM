// ESLint's own `no-restricted-syntax`, which oxlint does not ship, loaded as an oxlint JS plugin.
import { builtinRules } from "eslint/use-at-your-own-risk"

export default {
  meta: { name: "eslint-core" },
  rules: { "no-restricted-syntax": builtinRules.get("no-restricted-syntax") },
}
