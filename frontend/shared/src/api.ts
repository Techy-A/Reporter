/** Tiny API client shared by both portals. Each portal talks only to its own backend
 * (same origin via the dev proxy / reverse proxy), so cookies never cross portals. */

export class ApiError extends Error {
  constructor(public status: number, message: string, public fields?: string[]) {
    super(message);
  }
}

type Opts = { method?: string; json?: unknown; form?: FormData };

export async function api<T = unknown>(path: string, opts: Opts = {}): Promise<T> {
  const headers: Record<string, string> = { "x-pp-request": "1" };
  let body: BodyInit | undefined;
  if (opts.json !== undefined) {
    headers["content-type"] = "application/json";
    body = JSON.stringify(opts.json);
  } else if (opts.form) {
    body = opts.form;
  }
  const res = await fetch(path, {
    method: opts.method ?? (body ? "POST" : "GET"),
    headers,
    body,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(res.status, data?.detail ?? `Request failed (${res.status})`, data?.fields);
  }
  return data as T;
}

export function errorText(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 422 && e.fields?.length) return `Check these fields: ${e.fields.join(", ")}`;
    if (e.status === 429) return "Too many attempts. Wait a few minutes and try again.";
    return e.message;
  }
  return "Can't reach the server. Check that it's running.";
}
