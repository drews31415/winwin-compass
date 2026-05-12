const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type UserContext = {
  business_type?: string;
  area?: string;
  capital?: number;
  age?: number;
  is_new?: boolean;
  user_types?: string[];
  risk_score?: number;
};

export type Policy = {
  id?: string;
  program_nm?: string;
  title?: string;
  agency?: string;
  category?: string;
  target?: string;
  description?: string;
  budget_min?: number;
  budget_max?: number;
  apply_start?: string;
  apply_end?: string;
  source_url?: string;
  reason?: string;
  match_reason?: string;
  match_score?: number;
  score?: number;
  badges?: string[];
  priority?: string;
};

export type PolicyMatchParams = {
  business_type?: string;
  area?: string;
  capital?: number;
  age?: number;
  is_new?: boolean;
  user_types?: string[] | string;
  risk_score?: number;
};

export type AreaFilters = {
  gu_nm?: string;
  area_type?: string;
  q?: string;
};

export type Area = {
  area_cd: string;
  area_nm: string;
  gu_nm: string;
  area_type: string;
  geom_lat?: number;
  geom_lng?: number;
};

export type Report = {
  area_nm: string;
  risk_score: number;
  report_md: string;
  charts: {
    sales_trend: unknown[];
    time_slots: unknown[];
    age_distribution: unknown[];
  };
  matched_policies: Policy[];
};

export type ForecastPoint = {
  quarter: string;
  date: string;
  predicted_sales: number;
  lower_bound: number;
  upper_bound: number;
  trend: string;
};

export type ForecastResponse = {
  area_cd: string;
  area_nm: string;
  forecast: ForecastPoint[];
  trend_summary: string;
  confidence: number;
  chart_data: {
    labels: string[];
    predicted: number[];
    lower: number[];
    upper: number[];
  };
};

export type RiskFactor = {
  factor: string;
  value: string;
  contribution: number;
  description: string;
};

export type RiskResponse = {
  area_cd: string;
  risk_score: number;
  risk_level: string;
  risk_probability: number;
  main_risk_factors: RiskFactor[];
  score_breakdown: {
    sales_score: number;
    store_score: number;
    population_score: number;
  };
  compared_to_avg: string;
};

export type MarketingPurpose = "sns" | "review" | "flyer" | "menu" | "event" | "pivot";
export type MarketingTone = "friendly" | "premium" | "urgent" | "calm" | "young";

export type MarketingGenerateParams = {
  business_type: string;
  area: string;
  purpose: MarketingPurpose;
  tone: MarketingTone;
  target_customer?: string;
  risk_factors?: string[];
  offer?: string;
  menu_items?: string[];
  extra_context?: string;
};

export type MarketingContent = {
  title: string;
  channel: string;
  content: string;
  usage_tip: string;
};

export type MarketingGenerateResponse = {
  contents: MarketingContent[];
  action_checklist: string[];
  source: "openai" | "sample";
};

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text}`);
  }

  return res.json() as Promise<T>;
}

function queryString(params?: Record<string, string | number | boolean | string[] | undefined | null>) {
  const query = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      if (value.length) query.set(key, value.join(","));
      return;
    }
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  });
  const value = query.toString();
  return value ? `?${value}` : "";
}

export function sendChat(
  message: string,
  sessionId: string,
  userContext: UserContext = {},
): Promise<Response> {
  return fetch(`${BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      user_context: userContext,
    }),
  });
}

export function getAreas(filters?: AreaFilters): Promise<Area[]> {
  return apiFetch<Area[]>(`/api/v1/areas${queryString(filters)}`);
}

export function getReport(areaCd: string): Promise<Report> {
  return apiFetch<Report>(`/api/v1/report/${encodeURIComponent(areaCd)}`);
}

export function getForecast(areaCd: string, periods = 4): Promise<ForecastResponse> {
  return apiFetch<ForecastResponse>(`/api/v1/ml/forecast/${encodeURIComponent(areaCd)}${queryString({ periods })}`);
}

export function getRisk(areaCd: string): Promise<RiskResponse> {
  return apiFetch<RiskResponse>(`/api/v1/ml/risk/${encodeURIComponent(areaCd)}`);
}

export function matchPolicies(params: PolicyMatchParams): Promise<{ policies: Policy[]; total: number }> {
  return apiFetch<{ policies: Policy[]; total: number }>(`/api/v1/policy/match${queryString(params)}`);
}

export function searchPolicies(query: string): Promise<{ policies: Policy[] }> {
  return apiFetch<{ policies: Policy[] }>("/api/v1/policy/search", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

export function generateMarketing(
  params: MarketingGenerateParams,
): Promise<MarketingGenerateResponse> {
  return apiFetch<MarketingGenerateResponse>("/api/v1/marketing/generate", {
    method: "POST",
    body: JSON.stringify(params),
  });
}
