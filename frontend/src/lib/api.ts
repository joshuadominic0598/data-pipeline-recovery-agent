import type { Obj } from "../types";

let operatorToken = "";
export async function api(path: string, body?: Obj) {
  const r = await fetch(
    "/api" + path,
    body
      ? {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Operator-Token": operatorToken,
          },
          body: JSON.stringify(body),
        }
      : {},
  );
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(e.detail || "Request failed");
  }
  return r.json();
}

export function setOperatorToken(token: string) {
  operatorToken = token;
}
