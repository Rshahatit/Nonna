const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "API error");
  }
  return res.json();
}

// Elder types
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

export interface Session {
  id: string;
  elder_id: string;
  channel: "phone" | "pwa";
  status: "live" | "processing" | "complete" | "failed";
  started_at: string;
  ended_at: string | null;
  duration: number | null;
  topics_covered: string[];
  new_people_mentioned: string[];
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

// API functions
export const api = {
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
};
