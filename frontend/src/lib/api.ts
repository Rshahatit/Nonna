const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

let _getToken: (() => Promise<string | null>) | null = null;

export function setTokenProvider(fn: () => Promise<string | null>) {
  _getToken = fn;
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };

  // Add auth token if available
  if (_getToken) {
    const token = await _getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "API error");
  }
  return res.json();
}

// ──────────────────────────── Types ────────────────────────────

export interface CallSchedule {
  days: string[];
  time: string;
  timezone: string;
}

export interface Elder {
  id: string;
  name: string;
  phone_number: string;
  seed_context: string;
  call_schedule: CallSchedule;
  created_at: string;
  created_by: string;
}

export interface ElderMemory {
  people: { name: string; relationship: string; details: string[] }[];
  places: { name: string; significance: string }[];
  life_events: { event: string; approximate_date: string; details: string }[];
  themes: string[];
  recipes_and_skills: { name: string; description: string }[];
  story_gaps: string[];
  session_count: number;
  last_session_date: string | null;
  conversation_style: string;
}

export type SessionMode = "story" | "navigator" | "check_in" | "assist";

export interface NavigationContext {
  task: string | null;
  current_app: string | null;
  current_screen: string | null;
  steps_completed: string[];
  steps_remaining: string[];
  screens_analyzed: number;
  task_completed: boolean;
  stuck_count: number;
}

export interface Session {
  id: string;
  elder_id: string;
  channel: "phone" | "pwa";
  mode: SessionMode;
  status: "live" | "processing" | "complete" | "failed";
  started_at: string;
  ended_at: string | null;
  duration: number | null;
  topics_covered: string[];
  new_people_mentioned: string[];
  navigation_context: NavigationContext | null;
}

export interface Moment {
  id: string;
  title: string;
  summary: string;
  quote: string;
  visual_description: string;
  emotional_tone: string;
  image_url: string;
  order: number;
  tags: string[];
  people_mentioned: string[];
  place_mentioned: string | null;
}

export interface Reel {
  id: string;
  session_id: string;
  elder_id: string;
  status: "generating" | "ready" | "failed";
  video_url: string;
  thumbnail_url: string;
  duration: number | null;
  created_at: string;
}

// Phase 2 types
export interface UserProfile {
  id: string;
  email: string;
  name: string;
  photo_url: string;
  provider: string;
  created_at: string;
}

export interface Family {
  id: string;
  name: string;
  created_by: string;
  created_at: string;
  elder_ids: string[];
}

export interface NotificationPrefs {
  reel_ready: boolean;
  missed_calls: boolean;
  weekly_digest: boolean;
  channel: "sms" | "email" | "both";
}

export interface FamilyMember {
  user_id: string;
  role: "organizer" | "member" | "viewer";
  joined_at: string;
  notification_prefs: NotificationPrefs;
  name: string;
  email: string;
  photo_url: string;
}

export interface Invite {
  id: string;
  family_id: string;
  email: string | null;
  role: "member" | "viewer";
  token: string;
  created_by: string;
  created_at: string;
  redeemed_at: string | null;
  status: "pending" | "redeemed" | "expired";
  family_name: string;
  inviter_name: string;
}

export interface Collection {
  id: string;
  family_id: string;
  elder_id: string;
  name: string;
  description: string;
  cover_image_url: string;
  created_by: string;
  created_at: string;
  moment_refs: { session_id: string; moment_id: string }[];
  is_public: boolean;
}

export interface Thread {
  id: string;
  family_id: string;
  elder_id: string;
  type: "person" | "place" | "theme";
  name: string;
  moment_refs: { session_id: string; moment_id: string }[];
  generated_at: string;
  session_count: number;
}

export interface SearchResult {
  moment_id: string;
  session_id: string;
  title: string;
  summary: string;
  quote: string;
  emotional_tone: string;
  image_url: string;
  tags: string[];
  people_mentioned: string[];
  place_mentioned: string | null;
  order: number;
  session_date: string;
  channel: string;
}

export interface Book {
  id: string;
  family_id: string;
  elder_id: string;
  title: string;
  created_by: string;
  status: "generating" | "preview_ready" | "ordered" | "shipped";
  pdf_url: string;
  source_type: string;
  source_ids: string[];
  page_count: number;
  created_at: string;
}

// ──────────────────────────── API Functions ────────────────────────────

export const api = {
  // Phase 1 — Elders
  createElder: (data: {
    name: string;
    phone_number: string;
    seed_context: string;
    call_schedule: CallSchedule;
    created_by: string;
  }) => fetchApi<Elder>("/elders", { method: "POST", body: JSON.stringify(data) }),

  getElder: (id: string) => fetchApi<Elder>(`/elders/${id}`),

  updateSchedule: (id: string, schedule: CallSchedule) =>
    fetchApi<{ status: string }>(`/elders/${id}/schedule`, {
      method: "PUT",
      body: JSON.stringify({ call_schedule: schedule }),
    }),

  getMemory: (id: string) => fetchApi<ElderMemory>(`/elders/${id}/memory`),

  triggerCall: (id: string) =>
    fetchApi<{ status: string; call_sid: string }>(`/elders/${id}/call`, {
      method: "POST",
    }),

  listSessions: (elderId?: string) =>
    fetchApi<Session[]>(`/sessions${elderId ? `?elder_id=${elderId}` : ""}`),

  getSession: (id: string) => fetchApi<Session>(`/sessions/${id}`),

  getMoments: (sessionId: string) =>
    fetchApi<Moment[]>(`/sessions/${sessionId}/moments`),

  getReel: (sessionId: string) => fetchApi<Reel>(`/sessions/${sessionId}/reel`),

  // Phase 2 — Auth
  signIn: () => fetchApi<UserProfile>("/auth/signin", { method: "POST" }),

  getMe: () => fetchApi<UserProfile>("/auth/me"),

  getMyFamilies: () => fetchApi<Family[]>("/auth/me/families"),

  // Phase 2 — Families
  createFamily: (name: string) =>
    fetchApi<Family>("/families", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),

  getFamily: (familyId: string) => fetchApi<Family>(`/families/${familyId}`),

  updateFamily: (familyId: string, name: string) =>
    fetchApi<{ status: string }>(`/families/${familyId}`, {
      method: "PUT",
      body: JSON.stringify({ name }),
    }),

  listMembers: (familyId: string) =>
    fetchApi<FamilyMember[]>(`/families/${familyId}/members`),

  updateMember: (familyId: string, userId: string, data: Partial<FamilyMember>) =>
    fetchApi<{ status: string }>(`/families/${familyId}/members/${userId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  removeMember: (familyId: string, userId: string) =>
    fetchApi<{ status: string }>(`/families/${familyId}/members/${userId}`, {
      method: "DELETE",
    }),

  // Phase 2 — Invites
  createInvite: (familyId: string, data: { email?: string; role: string }) =>
    fetchApi<Invite>(`/families/${familyId}/invites`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listInvites: (familyId: string) =>
    fetchApi<Invite[]>(`/families/${familyId}/invites`),

  getInvite: (token: string) => fetchApi<Invite>(`/invites/${token}`),

  redeemInvite: (token: string) =>
    fetchApi<FamilyMember>(`/invites/${token}/redeem`, { method: "POST" }),

  revokeInvite: (familyId: string, inviteId: string) =>
    fetchApi<{ status: string }>(`/families/${familyId}/invites/${inviteId}`, {
      method: "DELETE",
    }),

  // Phase 2 — Collections
  createCollection: (familyId: string, data: { name: string; description?: string; elder_id: string }) =>
    fetchApi<Collection>(`/families/${familyId}/collections`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listCollections: (familyId: string) =>
    fetchApi<Collection[]>(`/families/${familyId}/collections`),

  getCollection: (familyId: string, collectionId: string) =>
    fetchApi<Collection>(`/families/${familyId}/collections/${collectionId}`),

  updateCollection: (familyId: string, collectionId: string, data: Partial<Collection>) =>
    fetchApi<{ status: string }>(`/families/${familyId}/collections/${collectionId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteCollection: (familyId: string, collectionId: string) =>
    fetchApi<{ status: string }>(`/families/${familyId}/collections/${collectionId}`, {
      method: "DELETE",
    }),

  addMomentToCollection: (familyId: string, collectionId: string, ref: { session_id: string; moment_id: string }) =>
    fetchApi<{ status: string }>(`/families/${familyId}/collections/${collectionId}/moments`, {
      method: "POST",
      body: JSON.stringify(ref),
    }),

  // Phase 2 — Threads
  listThreads: (familyId: string, elderId: string, type?: string) =>
    fetchApi<Thread[]>(
      `/families/${familyId}/elders/${elderId}/threads${type ? `?type=${type}` : ""}`
    ),

  getThread: (threadId: string) => fetchApi<Thread>(`/families/threads/${threadId}`),

  // Phase 2 — Search
  searchMoments: (
    familyId: string,
    elderId: string,
    params: {
      q?: string;
      tags?: string;
      people?: string;
      date_from?: string;
      date_to?: string;
      channel?: string;
    }
  ) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.set(k, v);
    });
    return fetchApi<{ results: SearchResult[]; count: number; query: string }>(
      `/families/${familyId}/elders/${elderId}/search?${query.toString()}`
    );
  },

  // Phase 2 — Books
  createBook: (familyId: string, data: { title: string; elder_id: string; source_type: string; source_ids: string[] }) =>
    fetchApi<Book>(`/families/${familyId}/books`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listBooks: (familyId: string) => fetchApi<Book[]>(`/families/${familyId}/books`),

  getBook: (bookId: string) => fetchApi<Book>(`/families/books/${bookId}`),
};
