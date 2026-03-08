/** Payload passed to `AiCostCalc.track()`. */
export interface EventPayload {
  customerId: string;
  revenueAmountInCents?: number;
  uniqueRequestToken?: string;
  eventType?: string;
  occurredAt?: string;
}

/** Usage data from a single AI API call. */
export interface UsageData {
  vendor: string;
  model: string;
  inputTokens: number;
  outputTokens: number;
}

/** Pricing data for a single model. */
export interface ModelPricing {
  slug: string;
  inputPricePer1M: number;
  outputPricePer1M: number;
}

/** Result of a cost calculation. */
export interface CostResult {
  model: string;
  inputCost: number;
  outputCost: number;
  totalCost: number;
  inputTokens?: number;
  outputTokens?: number;
  estimated?: boolean;
}

/** SDK configuration options. */
export interface AiCostCalcConfig {
  apiKey?: string;
  baseUrl?: string;
  flushIntervalMs?: number;
  maxRetries?: number;
  defaultEventType?: string;
  onError?: (error: AiCostCalcError) => void;
  debug?: boolean;
}

/** Error information surfaced via the `onError` callback. */
export interface AiCostCalcError {
  message: string;
  cause?: unknown;
}
