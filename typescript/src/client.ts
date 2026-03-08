import type {
  AiCostCalcConfig,
  AiCostCalcError,
  CostResult,
  EventPayload,
  ModelPricing,
  UsageData,
} from "./types.js";

const DEFAULT_BASE_URL = "https://margindash.com/api/v1";
const DEFAULT_FLUSH_INTERVAL_MS = 5_000;
const DEFAULT_MAX_RETRIES = 3;
const DEFAULT_EVENT_TYPE = "ai_request";
const MAX_QUEUE_SIZE = 1_000;
const BATCH_SIZE = 50;
const MAX_PENDING_USAGES = 1_000;
const SDK_VERSION = "1.3.6";
const HTTP_TIMEOUT_MS = 10_000;
const MAX_BACKOFF_MS = 30_000;

/** Internal wire format for events (snake_case). */
interface WireEvent {
  customer_id: string;
  revenue_amount_in_cents: number | null;
  vendor_responses: { vendor_name: string; ai_model_name: string; input_tokens: number; output_tokens: number }[];
  unique_request_token: string;
  event_type: string;
  occurred_at: string;
}

/**
 * ai-cost-calc client.
 *
 * Queues events in memory and flushes them to the API in
 * batches on a timer. Call {@link shutdown} when your process is about
 * to exit so that remaining events are delivered.
 */
export class AiCostCalc {
  private readonly apiKey: string;
  private readonly baseUrl: string;
  private readonly maxRetries: number;
  private readonly defaultEventType: string;
  private readonly onError?: (error: AiCostCalcError) => void;
  private readonly debug: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private flushTimer: any = null;
  private shutdownPromise: Promise<void> | null = null;
  private queue: WireEvent[] = [];
  private pendingUsages: UsageData[] = [];
  private readonly boundBeforeExit: () => void;
  private apiKeyWarned = false;

  // Pricing cache
  private pricingCache: Map<string, ModelPricing> | null = null;
  private pricingFetchedAt: number = 0;
  private pricingPromise: Promise<void> | null = null;
  private pricingFailedAt: number = 0;

  private static readonly PRICING_CACHE_TTL_MS = 86_400_000;   // 24 hours
  private static readonly PRICING_FAILURE_BACKOFF_MS = 60_000; // 60 seconds

  constructor(config: AiCostCalcConfig = {}) {
    this.apiKey = config.apiKey?.trim() ?? "";
    this.baseUrl = (config.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.maxRetries = config.maxRetries ?? DEFAULT_MAX_RETRIES;
    if (!Number.isInteger(this.maxRetries) || this.maxRetries < 0) {
      throw new Error("maxRetries must be a non-negative integer");
    }
    this.defaultEventType = config.defaultEventType ?? DEFAULT_EVENT_TYPE;
    this.onError = config.onError;
    this.debug = config.debug ?? false;

    // Only start background flush if we have an API key
    if (this.apiKey) {
      const intervalMs = config.flushIntervalMs ?? DEFAULT_FLUSH_INTERVAL_MS;
      if (!Number.isFinite(intervalMs) || intervalMs <= 0) {
        throw new Error("flushIntervalMs must be a finite number > 0");
      }
      this.flushTimer = setInterval(() => {
        void this.flush();
      }, intervalMs);

      if (this.flushTimer && typeof this.flushTimer.unref === "function") {
        this.flushTimer.unref();
      }
    }

    this.boundBeforeExit = () => { void this.shutdown(); };
    if (this.apiKey && typeof process !== "undefined" && typeof process.on === "function") {
      process.on("beforeExit", this.boundBeforeExit);
    }
  }

  /**
   * Calculate the cost of an AI API call using live pricing data.
   * No API key required — pricing is fetched from the public models endpoint.
   * Returns null if the model is unknown or pricing data is unavailable.
   *
   * Pass (model, inputTokens, outputTokens) for exact costs, or
   * (model, inputText, outputText?) for estimated costs using js-tiktoken.
   */
  async cost(model: string, inputTokens: number, outputTokens: number): Promise<CostResult | null>;
  async cost(model: string, inputText: string, outputText?: string): Promise<CostResult | null>;
  async cost(model: string, inputOrText: number | string, outputOrText?: number | string): Promise<CostResult | null> {
    try {
      let inputTokens: number;
      let outputTokens: number;
      let estimated = false;

      if (typeof inputOrText === "string") {
        if (outputOrText !== undefined && typeof outputOrText !== "string") {
          this.reportError({ message: "outputText must be a string when using text-based estimation" });
          return null;
        }
        const tokenizer = await this.loadTokenizer();
        if (!tokenizer) return null;
        inputTokens = tokenizer(inputOrText, model);
        outputTokens = typeof outputOrText === "string" ? tokenizer(outputOrText, model) : 0;
        estimated = true;
      } else if (typeof inputOrText === "number") {
        if (typeof outputOrText !== "number") {
          this.reportError({ message: "outputTokens is required when using token counts" });
          return null;
        }
        if (!Number.isInteger(inputOrText) || !Number.isInteger(outputOrText)
            || inputOrText < 0 || outputOrText < 0) {
          this.reportError({ message: "Token counts must be non-negative integers" });
          return null;
        }
        inputTokens = inputOrText;
        outputTokens = outputOrText;
      } else {
        this.reportError({ message: "Invalid arguments: pass (model, inputTokens, outputTokens) or (model, inputText, outputText?)" });
        return null;
      }

      await this.ensurePricing();
      const pricing = this.pricingCache?.get(model);
      if (!pricing) return null;

      const inputCost = (inputTokens * pricing.inputPricePer1M) / 1_000_000;
      const outputCost = (outputTokens * pricing.outputPricePer1M) / 1_000_000;
      return { model, inputCost, outputCost, totalCost: inputCost + outputCost, inputTokens, outputTokens, estimated };
    } catch (e) {
      this.reportError({ message: e instanceof Error ? e.message : "Unexpected error in cost()" });
      return null;
    }
  }

  private async loadTokenizer(): Promise<((text: string, model: string) => number) | null> {
    try {
      const { countTokens } = await import("./tokenizer.js");
      return countTokens;
    } catch {
      this.reportError({ message: "js-tiktoken is required for text-based cost estimation. Install it with: npm install js-tiktoken" });
      return null;
    }
  }

  addUsage(usage: UsageData): void {
    if (!this.requireApiKey("addUsage")) return;
    if (this.pendingUsages.length >= MAX_PENDING_USAGES) {
      this.log(`pendingUsages limit reached (${MAX_PENDING_USAGES}), dropping oldest entry`);
      this.pendingUsages.shift();
    }
    this.pendingUsages.push(usage);
  }

  /**
   * Enqueue an event for delivery. This method is synchronous and will
   * never throw -- errors are silently swallowed so that tracking can
   * never crash the host application.
   *
   * All usage entries previously added via {@link addUsage} are drained
   * and attached to the event.
   */
  track(event: EventPayload): void {
    if (!this.requireApiKey("track")) return;
    if (this.shutdownPromise !== null) return;
    try {
      const usages = this.pendingUsages;
      this.pendingUsages = [];
      const wire = this.toWireEvent(event, usages);
      this.enqueue(wire);
      this.log(`event enqueued (queue: ${this.queue.length})`);
    } catch (err) {
      this.reportError({ message: "Failed to enqueue event", cause: err });
    }
  }

  /**
   * Flush all queued events to the API immediately.
   */
  async flush(): Promise<void> {
    if (!this.apiKey) return;
    const batches = this.drain();
    if (batches.length === 0) return;
    const eventCount = batches.reduce((sum, b) => sum + b.length, 0);
    this.log(`flushing ${eventCount} ${eventCount === 1 ? "event" : "events"} in ${batches.length} ${batches.length === 1 ? "batch" : "batches"}`);
    await Promise.allSettled(batches.map((batch) => this.sendBatch(batch)));
  }

  /**
   * Flush remaining events and stop the background timer.
   * Call this before your process exits.
   */
  async shutdown(): Promise<void> {
    if (!this.apiKey) return;
    if (this.shutdownPromise !== null) return this.shutdownPromise;

    this.shutdownPromise = (async () => {
      if (typeof process !== "undefined" && typeof process.removeListener === "function") {
        process.removeListener("beforeExit", this.boundBeforeExit);
      }
      if (this.flushTimer !== null) {
        clearInterval(this.flushTimer);
        this.flushTimer = null;
      }
      await this.flush();
    })();

    return this.shutdownPromise;
  }

  // ---------------------------------------------------------------------------
  // API key guard
  // ---------------------------------------------------------------------------

  private requireApiKey(method: string): boolean {
    if (this.apiKey) return true;
    if (!this.apiKeyWarned) {
      this.reportError({ message: `apiKey required for ${method} — calls will be skipped` });
      this.apiKeyWarned = true;
    }
    return false;
  }

  // ---------------------------------------------------------------------------
  // Pricing
  // ---------------------------------------------------------------------------

  private async ensurePricing(): Promise<void> {
    const now = Date.now();

    // Cache is fresh
    if (this.pricingCache && (now - this.pricingFetchedAt) < AiCostCalc.PRICING_CACHE_TTL_MS) {
      return;
    }

    // Recently failed — back off, use stale cache
    if (this.pricingFailedAt && (now - this.pricingFailedAt) < AiCostCalc.PRICING_FAILURE_BACKOFF_MS) {
      return;
    }

    // Deduplicate concurrent fetches
    if (this.pricingPromise) return this.pricingPromise;

    this.pricingPromise = (async () => {
      try {
        const res = await fetch(`${this.baseUrl}/models`, {
          headers: { "User-Agent": `ai-cost-calc-node/${SDK_VERSION}` },
          signal: AbortSignal.timeout(HTTP_TIMEOUT_MS),
        });
        if (!res.ok) throw new Error(`status ${res.status}`);

        const data: {
          vendors: {
            vendor: string;
            models: { slug: string; input_price_per_1m: number; output_price_per_1m: number }[];
          }[];
        } = await res.json();

        const map = new Map<string, ModelPricing>();
        if (Array.isArray(data.vendors)) {
          for (const vendor of data.vendors) {
            if (typeof vendor !== "object" || vendor === null) continue;
            if (!Array.isArray(vendor.models)) continue;
            for (const m of vendor.models) {
              if (typeof m !== "object" || m === null) continue;
              const input = m.input_price_per_1m;
              const output = m.output_price_per_1m;
              if (!m.slug || !Number.isFinite(input) || !Number.isFinite(output)) continue;
              map.set(m.slug, {
                slug: m.slug,
                inputPricePer1M: input,
                outputPricePer1M: output,
              });
            }
          }
        }
        this.pricingCache = map;
        this.pricingFetchedAt = Date.now();
        this.pricingFailedAt = 0;
        this.log(`pricing loaded (${map.size} models)`);
      } catch (err) {
        this.pricingFailedAt = Date.now();
        this.reportError({ message: "Failed to fetch pricing data", cause: err });
      } finally {
        this.pricingPromise = null;
      }
    })();

    return this.pricingPromise;
  }

  // ---------------------------------------------------------------------------
  // Queue
  // ---------------------------------------------------------------------------

  private enqueue(event: WireEvent): void {
    if (this.queue.length >= MAX_QUEUE_SIZE) {
      this.queue.shift();
      this.log(`queue full (${MAX_QUEUE_SIZE}), dropping oldest event`);
    }
    this.queue.push(event);
  }

  private drain(): WireEvent[][] {
    if (this.queue.length === 0) return [];
    const all = this.queue;
    this.queue = [];
    const batches: WireEvent[][] = [];
    for (let i = 0; i < all.length; i += BATCH_SIZE) {
      batches.push(all.slice(i, i + BATCH_SIZE));
    }
    return batches;
  }

  // ---------------------------------------------------------------------------
  // Serialization
  // ---------------------------------------------------------------------------

  private toWireEvent(event: EventPayload, usages: UsageData[]): WireEvent {
    const wire: WireEvent = {
      customer_id: event.customerId,
      revenue_amount_in_cents: event.revenueAmountInCents ?? null,
      vendor_responses: usages.map((u) => ({
        vendor_name: u.vendor,
        ai_model_name: u.model,
        input_tokens: u.inputTokens,
        output_tokens: u.outputTokens,
      })),
      unique_request_token: event.uniqueRequestToken ?? crypto.randomUUID(),
      event_type: event.eventType ?? this.defaultEventType,
      occurred_at: event.occurredAt ?? new Date().toISOString(),
    };
    return wire;
  }

  // ---------------------------------------------------------------------------
  // HTTP
  // ---------------------------------------------------------------------------

  private async fetchWithRetry(url: string, init: RequestInit): Promise<Response> {
    let lastError: unknown;
    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        const res = await fetch(url, init);
        if (res.status >= 500 || res.status === 429) {
          lastError = res;
        } else {
          return res;
        }
      } catch (err) {
        lastError = err;
      }
      if (attempt < this.maxRetries) {
        const status = lastError instanceof Response ? `status ${lastError.status}` : "network error";
        this.log(`${status}, retrying (${attempt + 1}/${this.maxRetries})`);
        const base = Math.min(1000 * 2 ** attempt, MAX_BACKOFF_MS);
        await new Promise((r) => setTimeout(r, base + Math.random() * base * 0.5));
      }
    }
    throw lastError;
  }

  private async sendBatch(events: WireEvent[]): Promise<void> {
    try {
      const response = await this.fetchWithRetry(`${this.baseUrl}/events`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${this.apiKey}`,
          "User-Agent": `ai-cost-calc-node/${SDK_VERSION}`,
        },
        body: JSON.stringify({ events }),
        signal: AbortSignal.timeout(HTTP_TIMEOUT_MS),
      });

      this.log(`batch sent (status ${response.status}, ${events.length} ${events.length === 1 ? "event" : "events"})`);

      if (!response.ok) {
        let body = "";
        try { body = await response.text(); } catch { /* ignore */ }
        this.reportError({ message: `Request failed with status ${response.status}: ${body}` });
      }
    } catch (err) {
      const message = err instanceof Response
        ? `Request failed after retries (status ${err.status})`
        : "Request failed after retries";
      this.reportError({ message, cause: err });
    }
  }

  private reportError(error: AiCostCalcError): void {
    if (this.debug) console.error(`[ai-cost-calc] ${error.message}`);
    if (!this.onError) return;
    try {
      this.onError(error);
    } catch {
      // Never crash the host application.
    }
  }

  private log(msg: string): void {
    if (this.debug) console.debug(`[ai-cost-calc] ${msg}`);
  }
}
