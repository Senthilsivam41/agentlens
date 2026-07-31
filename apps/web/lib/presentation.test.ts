import {describe, expect, it} from "vitest";

import {label, percentage} from "./presentation";

describe("presentation", () => {
  it("formats coverage", () => expect(percentage(0.125)).toBe("12.5%"));
  it("labels machine values", () => expect(label("agent_logic_failure")).toBe("Agent Logic Failure"));
});

