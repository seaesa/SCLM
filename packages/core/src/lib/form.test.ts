// The expected messages are the Vietnamese UI text: cspell:disable
import { describe, expect, it, vi } from "vitest"

import { applyServerErrors, submitThen, translateApiCode } from "./form"

/** The shape `isAxiosError` recognises, so no real HTTP call is needed. */
function apiError(data: unknown) {
  return { isAxiosError: true, response: { data } }
}

function setErrorSpy() {
  return vi.fn<(name: string, error: { type: string; message: string }) => void>()
}

describe("translateApiCode", () => {
  it("translates a backend error code", () => {
    expect(translateApiCode("email_taken", "Email already registered")).toBe(
      "Email này đã được đăng ký"
    )
  })

  it("translates a pydantic error type with its params", () => {
    expect(translateApiCode("string_too_short", "too short", { min_length: 8 })).toBe(
      "Cần ít nhất 8 ký tự"
    )
  })

  it("falls back to the server message for an unknown code", () => {
    expect(translateApiCode("not_a_real_code", "Server said no")).toBe("Server said no")
  })
})

describe("applyServerErrors", () => {
  it("puts a field error on that field", () => {
    const setError = setErrorSpy()

    applyServerErrors(
      apiError({
        code: "email_taken",
        message: "Email already registered",
        details: [
          {
            field: "email",
            code: "email_taken",
            message: "Email already registered",
            params: null,
          },
        ],
      }),
      setError
    )

    expect(setError).toHaveBeenCalledExactlyOnceWith("email", {
      type: "server",
      message: "Email này đã được đăng ký",
    })
  })

  it("puts a 422 validation error on its dot path", () => {
    const setError = setErrorSpy()

    applyServerErrors(
      apiError({
        code: "validation_error",
        message: "Please check the highlighted fields",
        details: [
          {
            field: "password",
            code: "string_too_short",
            message: "String should have at least 8 characters",
            params: { min_length: 8 },
          },
        ],
      }),
      setError
    )

    expect(setError).toHaveBeenCalledExactlyOnceWith("password", {
      type: "server",
      message: "Cần ít nhất 8 ký tự",
    })
  })

  it("puts an error without details on root.server", () => {
    const setError = setErrorSpy()

    applyServerErrors(
      apiError({ code: "invalid_credentials", message: "Invalid email or password" }),
      setError
    )

    expect(setError).toHaveBeenCalledExactlyOnceWith("root.server", {
      type: "server",
      message: "Email hoặc mật khẩu không đúng",
    })
  })

  it("treats a network failure as a root error", () => {
    const setError = setErrorSpy()

    applyServerErrors({ isAxiosError: true, response: undefined }, setError)

    expect(setError).toHaveBeenCalledExactlyOnceWith("root.server", {
      type: "server",
      message: "Không kết nối được máy chủ. Kiểm tra lại mạng.",
    })
  })
})

describe("submitThen", () => {
  it("submits even when no success callback is given", async () => {
    const submit = vi.fn<(values: { email: string }) => Promise<string>>(
      async (values) => values.email
    )

    await submitThen({ email: "a@example.com" }, submit)

    expect(submit).toHaveBeenCalledWith({ email: "a@example.com" })
  })

  it("passes the result and values to the success callback", async () => {
    const onSuccess = vi.fn<(result: string, values: { id: number }) => void>()

    await submitThen({ id: 1 }, async () => "ok", onSuccess)

    expect(onSuccess).toHaveBeenCalledWith("ok", { id: 1 })
  })
})
