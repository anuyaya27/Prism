import { EvaluateRequestPayload } from "../types";

const envBase = import.meta.env.VITE_API_BASE_URL;
export const API_BASE_URL = envBase || "http://127.0.0.1:8000";
console.info(`[api] VITE_API_BASE_URL=${envBase ?? "undefined"}; using API base URL: ${API_BASE_URL}`);

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${init?.method || "GET"} ${path} failed: ${res.status} ${text}`);
    }
    return res.json();
  } catch (err) {
    console.error(`[api] request failed for ${path}`, err);
    throw err;
  }
}

export function getModels() {
  return request("/models");
}

export function postEvaluate(body: EvaluateRequestPayload, signal?: AbortSignal) {
  return request("/evaluate", { method: "POST", body: JSON.stringify(body), signal });
}

export function debugPing() {
  return request("/debug/ping");
}
