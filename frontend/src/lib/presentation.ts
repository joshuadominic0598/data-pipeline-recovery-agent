export const stages = [
  "ingestion",
  "cleaning",
  "preprocessing",
  "business_rules",
  "consumption",
];
export const stageLabels = [
  "Ingest",
  "Clean",
  "Preprocess",
  "Apply rules",
  "Publish",
];
export const busy = [
  "queued",
  "running",
  "investigating",
  "testing",
  "approved",
  "applying",
  "verifying",
];
export const pretty = (s: string) =>
  s.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
export const time = (s?: string) =>
  s
    ? new Date(s).toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZone: "Asia/Kolkata",
      })
    : "—";
