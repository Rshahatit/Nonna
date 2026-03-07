"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Elder, type Session, type Moment, type Reel } from "@/lib/api";
import Link from "next/link";

interface SessionWithDetails extends Session {
  moments?: Moment[];
  reel?: Reel;
}

export default function ArchivePage() {
  const params = useParams();
  const elderId = params.elderId as string;

  const [elder, setElder] = useState<Elder | null>(null);
  const [sessions, setSessions] = useState<SessionWithDetails[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [elderData, sessionData] = await Promise.all([
          api.getElder(elderId),
          api.listSessions(elderId),
        ]);
        setElder(elderData);
        setSessions(sessionData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [elderId]);

  const loadSessionDetails = async (sessionId: string) => {
    setSelectedSession(sessionId);
    const session = sessions.find((s) => s.id === sessionId);
    if (session?.moments) return; // Already loaded

    try {
      const [moments, reel] = await Promise.all([
        api.getMoments(sessionId),
        api.getReel(sessionId).catch(() => null),
      ]);
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? { ...s, moments: moments, reel: reel ?? undefined }
            : s
        )
      );
    } catch {
      // Moments might not be ready yet
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <p className="text-xl text-nonna-brown/60">Loading archive...</p>
      </main>
    );
  }

  if (error || !elder) {
    return (
      <main className="min-h-screen flex items-center justify-center px-6">
        <div className="text-center space-y-4">
          <p className="text-xl text-red-600">{error || "Elder not found"}</p>
          <Link href="/" className="text-nonna-accent hover:underline">
            Go home
          </Link>
        </div>
      </main>
    );
  }

  const selected = sessions.find((s) => s.id === selectedSession);

  return (
    <main className="min-h-screen px-6 py-12 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-12">
        <h1 className="text-4xl font-serif font-bold mb-2">
          {elder.name}&apos;s Stories
        </h1>
        <p className="text-nonna-brown/60">
          {sessions.length === 0
            ? "No conversations yet. Nonna will call soon!"
            : `${sessions.length} conversation${sessions.length !== 1 ? "s" : ""} so far`}
        </p>
        <Link
          href={`/talk/${elderId}`}
          className="inline-block mt-4 text-nonna-accent hover:underline"
        >
          Start a video conversation &rarr;
        </Link>
      </div>

      {/* Sessions Grid */}
      {sessions.length === 0 ? (
        <div className="text-center py-20 bg-white/50 rounded-2xl">
          <p className="text-2xl text-nonna-brown/40 mb-4">
            Nonna is crafting her first conversation...
          </p>
          <p className="text-nonna-brown/30">
            Memory Reels will appear here after each chat.
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-6">
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => loadSessionDetails(session.id)}
              className={`text-left bg-white rounded-2xl p-6 shadow-sm
                         hover:shadow-md transition-shadow ${
                           selectedSession === session.id
                             ? "ring-2 ring-nonna-accent"
                             : ""
                         }`}
            >
              <div className="flex items-center gap-3 mb-3">
                <span className="text-2xl">
                  {session.channel === "phone" ? "\u{1F4DE}" : "\u{1F4F9}"}
                </span>
                <span className="text-sm text-nonna-brown/50">
                  {new Date(session.started_at).toLocaleDateString("en-US", {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                  })}
                </span>
              </div>
              <div className="flex items-center gap-2 mb-2">
                {session.status === "complete" && (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">
                    Reel Ready
                  </span>
                )}
                {session.status === "processing" && (
                  <span className="text-xs bg-nonna-warm text-nonna-brown px-2 py-1 rounded-full">
                    Creating Reel...
                  </span>
                )}
                {session.status === "live" && (
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full animate-pulse">
                    Live Now
                  </span>
                )}
                {session.duration && (
                  <span className="text-xs text-nonna-brown/40">
                    {Math.round(session.duration / 60)} min
                  </span>
                )}
              </div>
              {session.topics_covered.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {session.topics_covered.slice(0, 4).map((topic) => (
                    <span
                      key={topic}
                      className="text-xs bg-nonna-warm/50 text-nonna-brown/70 px-2 py-1 rounded-full"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Selected Session Detail */}
      {selected && (
        <div className="mt-12 space-y-8">
          <h2 className="text-2xl font-serif font-bold">
            {new Date(selected.started_at).toLocaleDateString("en-US", {
              weekday: "long",
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </h2>

          {/* Reel Player */}
          {selected.reel?.status === "ready" && selected.reel.video_url && (
            <div className="bg-black rounded-2xl overflow-hidden">
              <video
                src={selected.reel.video_url}
                controls
                className="w-full max-h-[500px]"
                poster={selected.reel.thumbnail_url || undefined}
              />
            </div>
          )}

          {selected.reel?.status === "generating" && (
            <div className="bg-nonna-warm/30 rounded-2xl p-12 text-center">
              <p className="text-xl text-nonna-brown/60">
                Nonna is crafting this memory...
              </p>
              <p className="text-nonna-brown/40 mt-2">
                The Memory Reel will appear here when it&apos;s ready.
              </p>
            </div>
          )}

          {/* Moments */}
          {selected.moments && selected.moments.length > 0 && (
            <div className="space-y-6">
              <h3 className="text-xl font-semibold">Story Moments</h3>
              {selected.moments.map((moment) => (
                <div
                  key={moment.id}
                  className="bg-white rounded-2xl p-6 shadow-sm flex gap-6"
                >
                  {moment.image_url && (
                    <img
                      src={moment.image_url}
                      alt={moment.title}
                      className="w-40 h-28 rounded-xl object-cover flex-shrink-0"
                    />
                  )}
                  <div>
                    <h4 className="font-bold text-lg mb-1">{moment.title}</h4>
                    <p className="text-nonna-brown/80 mb-2">
                      {moment.summary}
                    </p>
                    {moment.quote && (
                      <blockquote className="italic text-nonna-brown/60 border-l-2 border-nonna-gold pl-3">
                        &ldquo;{moment.quote}&rdquo;
                      </blockquote>
                    )}
                    <span className="inline-block mt-2 text-xs bg-nonna-warm/50 text-nonna-brown/60 px-2 py-1 rounded-full capitalize">
                      {moment.emotional_tone}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </main>
  );
}
