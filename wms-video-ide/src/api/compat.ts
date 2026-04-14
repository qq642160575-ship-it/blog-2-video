import { ensureOk } from './client';

export const openGenerateScriptSse = async (payload: {
  source_text: string;
  thread_id?: string | null;
}): Promise<Response> => {
  const response = await fetch('/api/generate_script_sse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return ensureOk(response);
};
