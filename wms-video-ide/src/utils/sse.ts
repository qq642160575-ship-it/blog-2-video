export const readSse = async (
  response: Response,
  onPayload: (payload: any) => void
) => {
  const reader = response.body?.getReader();
  if (!reader) throw new Error('No readable stream');
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const dataStr = line.slice(6).trim();
        if (dataStr === '[DONE]') continue;
        try {
          const payload = JSON.parse(dataStr);
          onPayload(payload);
        } catch (err) {
          console.error('SSE parse error:', err, dataStr);
        }
      }
    }
  }
};
