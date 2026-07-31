export function percentage(value: number): string {
  return new Intl.NumberFormat("en", {style: "percent", maximumFractionDigits: 1}).format(value);
}

export function compact(value: number): string {
  return new Intl.NumberFormat("en", {notation: "compact", maximumFractionDigits: 1}).format(value);
}

export function label(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

