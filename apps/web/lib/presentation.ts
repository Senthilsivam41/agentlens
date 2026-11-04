export function percentage(value: number): string {
  return new Intl.NumberFormat("en", {style: "percent", maximumFractionDigits: 1}).format(value);
}

export function compact(value: number): string {
  return new Intl.NumberFormat("en", {notation: "compact", maximumFractionDigits: 1}).format(value);
}

export function label(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

export function isDemoIdentity(agentName: string, environment: string): boolean {
  return environment === "demo" || agentName === "demo-support-agent";
}

export type ActionTone = "red" | "orange" | "green";

export type ActionSignal = {
  tone: ActionTone;
  name: "Red" | "Orange" | "Green";
  action: "Act" | "Review" | "No action";
};

const RED_CAUSES = new Set(["agent_logic_failure", "tool_runtime_failure"]);
const ORANGE_CAUSES = new Set(["user_prompt_ambiguity", "high_volatility"]);

/** Structural volatility at or above this value is a review, matching the score worker. */
export const VOLATILITY_REVIEW = 4;

export function actionSignal(rootCause: string | null | undefined): ActionSignal | null {
  if (!rootCause) return null;
  if (RED_CAUSES.has(rootCause)) return {tone: "red", name: "Red", action: "Act"};
  if (ORANGE_CAUSES.has(rootCause)) return {tone: "orange", name: "Orange", action: "Review"};
  return {tone: "green", name: "Green", action: "No action"};
}

export function distanceTone(isDrifted: boolean | null | undefined, distance: number | null | undefined): ActionTone | "neutral" {
  if (isDrifted === true) return "red";
  if (distance == null) return "neutral";
  return "green";
}

export function ambiguityTone(score: number | null | undefined, threshold: number | null | undefined): ActionTone | "neutral" {
  if (score == null || threshold == null) return "neutral";
  return score > threshold ? "orange" : "green";
}

export function volatilityTone(value: number | null | undefined): ActionTone | "neutral" {
  if (value == null) return "neutral";
  return value >= VOLATILITY_REVIEW ? "orange" : "green";
}

export function distanceDetail(tone: ActionTone | "neutral"): string {
  if (tone === "red") return "Red. Above the baseline.";
  if (tone === "green") return "Green. Inside the baseline.";
  return "Not compared with a baseline.";
}

export function ambiguityDetail(tone: ActionTone | "neutral"): string {
  if (tone === "orange") return "Orange. Review the prompt.";
  if (tone === "green") return "Green. Prompt is specific.";
  return "Ambiguity was not scored.";
}

export function volatilityDetail(tone: ActionTone | "neutral"): string {
  if (tone === "orange") return "Orange. Review the tool path.";
  if (tone === "green") return "Green. Path is stable.";
  return "Volatility unavailable.";
}

