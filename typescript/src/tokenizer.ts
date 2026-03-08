import { encodingForModel, getEncoding, type Tiktoken } from "js-tiktoken";

const cache = new Map<string, Tiktoken>();
const MAX_CACHE_SIZE = 128;
const MAX_TEXT_LENGTH = 1_000_000;

export function countTokens(text: string, model: string): number {
  if (text.length > MAX_TEXT_LENGTH) throw new Error("Text exceeds 1MB limit");
  let enc = cache.get(model);
  if (!enc) {
    if (cache.size >= MAX_CACHE_SIZE) {
      const firstKey = cache.keys().next().value!;
      cache.delete(firstKey);
    }
    try {
      enc = encodingForModel(model as Parameters<typeof encodingForModel>[0]);
    } catch {
      enc = getEncoding("cl100k_base");
    }
    cache.set(model, enc);
  }
  return enc.encode(text).length;
}
