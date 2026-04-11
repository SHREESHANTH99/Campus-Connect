// src/lib/api.ts
import type { FeedResponse, Confession, VoteResult, Comment } from "@/types/confession";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

function token() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("cc_token");
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function req<T>(path: string, init: RequestInit = {}, auth = false): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(init.headers as any) };
  if (auth && token()) headers["Authorization"] = `Bearer ${token()}`;
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { msg = (await res.json()).detail ?? msg; } catch {}
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  confessions: {
    feed: (p: { sort?: string; category?: string; college_id?: string; cursor?: string; limit?: number }) => {
      const q = new URLSearchParams();
      if (p.sort)       q.set("sort",       p.sort);
      if (p.category)   q.set("category",   p.category);
      if (p.college_id) q.set("college_id", p.college_id);
      if (p.cursor)     q.set("cursor",     p.cursor);
      if (p.limit)      q.set("limit",      String(p.limit));
      return req<FeedResponse>(`/confessions?${q}`);
    },
    get:     (id: string) => req<Confession>(`/confessions/${id}`),
    create:  (body: { content: string; category: string; college_id?: string }) =>
      req<Confession>("/confessions/", { method: "POST", body: JSON.stringify(body) }, true),
    vote:    (id: string, vote_type: string) =>
      req<VoteResult>(`/confessions/${id}/vote`, { method: "POST", body: JSON.stringify({ vote_type }) }, true),
    react:   (id: string, reaction: string) =>
      req(`/confessions/${id}/react`, { method: "POST", body: JSON.stringify({ reaction }) }),
    report:  (id: string, reason: string, description?: string) =>
      req(`/confessions/${id}/report`, { method: "POST", body: JSON.stringify({ reason, description }) }, true),
    weekly:  () => req<Confession[]>("/confessions/trending/weekly"),
    comments: (id: string) => req<Comment[]>(`/confessions/${id}/comments`),
    comment:  (id: string, content: string, parent_id?: string) =>
      req<Comment>(`/confessions/${id}/comments`, { method: "POST", body: JSON.stringify({ content, parent_id }) }, true),
  },
  auth: {
    requestOtp: (phone: string) =>
      req("/auth/request-otp", { method: "POST", body: JSON.stringify({ phone }) }),
    verifyOtp:  (phone: string, otp: string) =>
      req<{ access_token: string; anonymous_username: string; is_new_user: boolean }>(
        "/auth/verify-otp", { method: "POST", body: JSON.stringify({ phone, otp }) }),
    me: () => req<{ id: string; anonymous_username: string; karma: number }>("/auth/me", {}, true),
  },
  events: {
    list: (p: { category?: string; search?: string; sort?: string; cursor?: string; limit?: number } = {}) => {
      const q = new URLSearchParams();
      if (p.category) q.set("category", p.category);
      if (p.search) q.set("search", p.search);
      if (p.sort) q.set("sort", p.sort);
      if (p.cursor) q.set("cursor", p.cursor);
      if (p.limit) q.set("limit", String(p.limit));
      return req<any[]>(`/events?${q}`);
    },
    get: (id: string) => req<any>(`/events/${id}`),
    create: (body: any) => req<any>("/events/", { method: "POST", body: JSON.stringify(body) }, true),
    rsvp: (id: string) => req<any>(`/events/${id}/rsvp`, { method: "POST" }, true),
    attendees: (id: string, p: { cursor?: string; limit?: number } = {}) => {
      const q = new URLSearchParams();
      if (p.cursor) q.set("cursor", p.cursor);
      if (p.limit) q.set("limit", String(p.limit));
      return req<{ items: any[] }>(`/events/${id}/attendees?${q}`).then((r) => r.items ?? []);
    },
    update: (id: string, body: any) => req<any>(`/events/${id}`, { method: "PUT", body: JSON.stringify(body) }, true),
    cancel: (id: string) => req<any>(`/events/${id}`, { method: "DELETE" }, true),
  },
  clubs: {
    list: (p: { category?: string; search?: string; limit?: number } = {}) => {
      const q = new URLSearchParams();
      if (p.category) q.set("category", p.category);
      if (p.search) q.set("search", p.search);
      if (p.limit) q.set("limit", String(p.limit));
      return req<any[]>(`/clubs?${q}`);
    },
    get: (id: string) => req<any>(`/clubs/${id}`),
    create: (body: any) => req<any>("/clubs/", { method: "POST", body: JSON.stringify(body) }, true),
    join: (id: string) => req<any>(`/clubs/${id}/join`, { method: "POST" }, true),
    members: (id: string, p: { cursor?: string; limit?: number } = {}) => {
      const q = new URLSearchParams();
      if (p.cursor) q.set("cursor", p.cursor);
      if (p.limit) q.set("limit", String(p.limit));
      return req<{ items: any[] }>(`/clubs/${id}/members?${q}`).then((r) => r.items ?? []);
    },
    events: (id: string, limit = 20) => req<any[]>(`/clubs/${id}/events?limit=${limit}`),
    update: (id: string, body: any) => req<any>(`/clubs/${id}`, { method: "PUT", body: JSON.stringify(body) }, true),
  },
  notifications: {
    list: () => req<any[]>("/notifications/", {}, true),
    readAll: () => req<any>("/notifications/read-all", { method: "POST" }, true),
    readOne: (id: string) => req<any>(`/notifications/${id}/read`, { method: "PATCH" }, true),
  },
  polls: {
    list: (limit = 20) => req<{ items: any[] }>(`/polls?limit=${limit}`).then((r) => r.items ?? []),
    create: (body: { question: string; options: string[]; ends_at?: string }) =>
      req<any>("/polls/", { method: "POST", body: JSON.stringify(body) }, true),
    vote: (id: string, option_index: number) =>
      req<any>(`/polls/${id}/vote`, { method: "POST", body: JSON.stringify({ option_index }) }, true),
    get: (id: string) => req<any>(`/polls/${id}`),
    results: (id: string) => req<any>(`/polls/${id}/results`),
  },
  search: {
    all: (q: string, scope: "all" | "confessions" | "events" | "clubs" = "all", limit = 20) =>
      req<any>(`/search?q=${encodeURIComponent(q)}&scope=${scope}&limit=${limit}`),
  },
  profile: {
    me: () => req<any>("/profile/me", {}, true),
    updateMe: (body: { college_id?: string; branch?: string; year?: number; bio?: string }) =>
      req<any>("/profile/me", { method: "PATCH", body: JSON.stringify(body) }, true),
    myConfessions: () => req<any[]>("/profile/me/confessions", {}, true),
    myEvents: () => req<any[]>("/profile/me/events", {}, true),
    myClubs: () => req<any[]>("/profile/me/clubs", {}, true),
  },
};
