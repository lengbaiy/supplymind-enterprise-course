export type SseEvent = { event: string; data: Record<string, unknown> };

export function parseSseEvents(text: string): SseEvent[] {
  return text.split("\n\n").flatMap((block) => {
    const event = block.match(/^event: (.+)$/m)?.[1];
    const raw = block.match(/^data: (.+)$/m)?.[1];
    if (!event || !raw) return [];
    try {
      return [{ event, data: JSON.parse(raw) as Record<string, unknown> }];
    } catch {
      return [];
    }
  });
}
