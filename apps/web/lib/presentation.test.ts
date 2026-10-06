import {describe, expect, it} from "vitest";

import {actionSignal, ambiguityTone, distanceTone, isDemoIdentity, label, percentage, volatilityTone} from "./presentation";

describe("presentation", () => {
  it("formats coverage", () => expect(percentage(0.125)).toBe("12.5%"));
  it("labels machine values", () => expect(label("agent_logic_failure")).toBe("Agent Logic Failure"));
  it("recognizes demo traffic", () => {
    expect(isDemoIdentity("demo-support-agent", "demo")).toBe(true);
    expect(isDemoIdentity("research-agent", "production")).toBe(false);
  });
  it("flags drift as act, review, or no action", () => {
    expect(actionSignal("tool_runtime_failure")).toMatchObject({tone: "red", action: "Act"});
    expect(actionSignal("agent_logic_failure")).toMatchObject({tone: "red", action: "Act"});
    expect(actionSignal("user_prompt_ambiguity")).toMatchObject({tone: "orange", action: "Review"});
    expect(actionSignal("high_volatility")).toMatchObject({tone: "orange", action: "Review"});
    expect(actionSignal("compliant")).toMatchObject({tone: "green", action: "No action"});
    expect(actionSignal(null)).toBeNull();
  });
  it("colors each drift metric", () => {
    expect(distanceTone(true, 12)).toBe("red");
    expect(distanceTone(false, 1.2)).toBe("green");
    expect(distanceTone(null, null)).toBe("neutral");
    expect(ambiguityTone(6, 3)).toBe("orange");
    expect(ambiguityTone(2, 3)).toBe("green");
    expect(volatilityTone(4)).toBe("orange");
    expect(volatilityTone(0.4)).toBe("green");
  });
});

