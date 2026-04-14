async function parseJsonSafely(response: Response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function ensureOk(response: Response): Promise<Response> {
  if (response.ok) return response;
  const body = await parseJsonSafely(response);
  const message =
    typeof body === 'string'
      ? body
      : (body as { detail?: string } | null)?.detail || `HTTP error! status: ${response.status}`;
  throw new Error(message);
}

export async function fetchJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  await ensureOk(response);
  return (await response.json()) as T;
}

export async function postJson<T>(
  input: RequestInfo | URL,
  body: unknown,
  init?: RequestInit
): Promise<T> {
  return fetchJson<T>(input, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    body: JSON.stringify(body),
    ...init,
  });
}
