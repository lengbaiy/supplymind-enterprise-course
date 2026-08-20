import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { getApiErrorMessage, getApiErrorState } from "./api-errors";

describe("API error mapping", () => {
  it.each([[401, "authentication"], [403, "forbidden"], [404, "not-found"], [409, "conflict"], [422, "validation"], [429, "rate-limited"], [500, "server"]] as const)("maps status %s to %s", (status, expected) => expect(getApiErrorState(new ApiError(status, "failed"))).toBe(expected));
  it("uses a recovery-focused network message", () => expect(getApiErrorMessage("network")).toContain("检查网络"));
});
