"use client";

import { useParams, useSearchParams, useRouter } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import {
  api, setTokenProvider,
  type Elder, type Session, type Moment, type Reel,
  type Thread, type Collection, type SearchResult,
} from "@/lib/api";
import { NavHeader } from "@/components/NavHeader";
import Link from "next/link";

type ViewTab = "timeline" | "people" | "themes" | "collections";

interface SessionWithDetails extends Session {
  moments?: Moment[];
  reel?: Reel;
}

export default function FamilyArchivePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const familyId = params.familyId as string;
  const elderId = params.elderId as string;

  const { user, loading: authLoading, getToken } = useAuth();

  const [elder, setElder] = useState<Elder | null>(null);
  const [sessions, setSessions] = useState<SessionWithDetails[]>([]);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [selectedMoment, setSelectedMoment] = useState<Moment | null>(null);

  const [activeTab, setActiveTab] = useState<ViewTab>(
    (searchParams.get("view") as ViewTab) || "timeline"
  );
  const [searchQuery, setSearchQuery] = useState(searchParams.get("q") || "");
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [activeTags, setActiveTags] = useState<string[]>([]);
  const [activePeople, setActivePeople] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [loading, setLoading] = useState(true);
  const [familyName, setFamilyName] = useState("");
  const [addToCollectionMoment, setAddToCollectionMoment] = useState<{ sessionId: string; momentId: string } | null>(null);
  const [collectionToast, setCollectionToast] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/");
      return;
    }
    setTokenProvider(getToken);

    async function load() {
      try {
        const [elderData, sessionData, familyData] = await Promise.all([
          api.getElder(elderId),
          api.listSessions(elderId),
          api.getFamily(familyId),
        ]);
        setElder(elderData);
        setSessions(sessionData);
        setFamilyName(familyData.name);

        // Load threads and collections
        const [threadData, collectionData] = await Promise.all([
          api.listThreads(familyId, elderId).catch(() => []),
          api.listCollections(familyId).catch(() => []),
        ]);
        setThreads(threadData);
        setCollections(collectionData);
      } catch {
        // handle error
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user, authLoading, elderId, familyId, getToken, router]);

  const loadSessionDetails = async (sessionId: string) => {
    setSelectedSession(sessionId);
    setSelectedMoment(null);
    const session = sessions.find((s) => s.id === sessionId);
    if (session?.moments) return;

    try {
      const [moments, reel] = await Promise.all([
        api.getMoments(sessionId),
        api.getReel(sessionId).catch(() => null),
      ]);
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId ? { ...s, moments, reel: reel ?? undefined } : s
        )
      );
    } catch {
      // Moments might not be ready
    }
  };

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim() && activeTags.length === 0 && activePeople.length === 0) {
      setSearchResults(null);
      return;
    }
    try {
      const result = await api.searchMoments(familyId, elderId, {
        q: searchQuery,
        tags: activeTags.length > 0 ? activeTags.join(",") : undefined,
        people: activePeople.length > 0 ? activePeople.join(",") : undefined,
      });
      setSearchResults(result.results);
    } catch {
      setSearchResults([]);
    }
  }, [searchQuery, activeTags, activePeople, familyId, elderId]);

  useEffect(() => {
    const timer = setTimeout(handleSearch, 300);
    return () => clearTimeout(timer);
  }, [handleSearch]);

  const handleAddToCollection = async (collectionId: string) => {
    if (!addToCollectionMoment) return;
    try {
      await api.addMomentToCollection(familyId, collectionId, {
        session_id: addToCollectionMoment.sessionId,
        moment_id: addToCollectionMoment.momentId,
      });
      const coll = collections.find((c) => c.id === collectionId);
      setCollectionToast(`Added to "${coll?.name}"`);
      // Update local collection state
      setCollections((prev) =>
        prev.map((c) =>
          c.id === collectionId
            ? { ...c, moment_refs: [...c.moment_refs, { session_id: addToCollectionMoment.sessionId, moment_id: addToCollectionMoment.momentId }] }
            : c
        )
      );
      setTimeout(() => setCollectionToast(null), 3000);
    } catch {
      setCollectionToast("Failed to add moment");
      setTimeout(() => setCollectionToast(null), 3000);
    }
    setAddToCollectionMoment(null);
  };

  // Derived data
  const personThreads = threads.filter((t) => t.type === "person");
  const placeThreads = threads.filter((t) => t.type === "place");
  const themeThreads = threads.filter((t) => t.type === "theme");

  const allTags = [
    "recipe", "life_lesson", "family_history", "skill_craft",
    "tradition", "humor", "love_story", "hardship", "achievement", "daily_life",
  ];

  const allPeople = Array.from(
    new Set(personThreads.map((t) => t.name))
  ).sort();

  const tagDisplayName: Record<string, string> = {
    recipe: "Recipes", life_lesson: "Life Lessons", family_history: "Family History",
    skill_craft: "Skills & Crafts", tradition: "Traditions", humor: "Funny Stories",
    love_story: "Love Stories", hardship: "Hardship", achievement: "Achievements",
    daily_life: "Daily Life",
  };

  const selected = sessions.find((s) => s.id === selectedSession);

  if (authLoading || loading) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <p className="text-xl text-nonna-brown/60">Loading archive...</p>
      </main>
    );
  }

  if (!elder) {
    return (
      <main className="min-h-screen flex items-center justify-center px-6">
        <div className="text-center space-y-4">
          <p className="text-xl text-red-600">Elder not found</p>
          <Link href="/dashboard" className="text-nonna-accent hover:underline">
            Go to dashboard
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen">
      <NavHeader familyName={familyName} />

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
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
            className="inline-block mt-2 text-nonna-accent hover:underline text-sm"
          >
            Start a video conversation
          </Link>
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <div className="flex gap-3">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={`Search ${elder.name}'s stories...`}
              className="flex-1 text-lg p-4 rounded-xl border-2 border-nonna-warm
                         focus:border-nonna-accent bg-white"
            />
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-4 py-2 rounded-xl border-2 transition-colors ${
                showFilters || activeTags.length > 0 || activePeople.length > 0
                  ? "border-nonna-accent bg-nonna-accent/10 text-nonna-accent"
                  : "border-nonna-warm text-nonna-brown/60 hover:border-nonna-accent"
              }`}
            >
              Filters {(activeTags.length + activePeople.length) > 0 && `(${activeTags.length + activePeople.length})`}
            </button>
          </div>

          {/* Filter panel */}
          {showFilters && (
            <div className="mt-3 p-4 bg-white rounded-xl border border-nonna-warm space-y-3">
              <div>
                <p className="text-sm font-semibold text-nonna-brown/60 mb-2">Topics</p>
                <div className="flex flex-wrap gap-2">
                  {allTags.map((tag) => (
                    <button
                      key={tag}
                      onClick={() =>
                        setActiveTags((prev) =>
                          prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
                        )
                      }
                      className={`text-sm px-3 py-1 rounded-full transition-colors ${
                        activeTags.includes(tag)
                          ? "bg-nonna-accent text-white"
                          : "bg-nonna-warm/50 text-nonna-brown/70 hover:bg-nonna-warm"
                      }`}
                    >
                      {tagDisplayName[tag] || tag}
                    </button>
                  ))}
                </div>
              </div>
              {allPeople.length > 0 && (
                <div>
                  <p className="text-sm font-semibold text-nonna-brown/60 mb-2">People</p>
                  <div className="flex flex-wrap gap-2">
                    {allPeople.map((person) => (
                      <button
                        key={person}
                        onClick={() =>
                          setActivePeople((prev) =>
                            prev.includes(person) ? prev.filter((p) => p !== person) : [...prev, person]
                          )
                        }
                        className={`text-sm px-3 py-1 rounded-full transition-colors ${
                          activePeople.includes(person)
                            ? "bg-nonna-accent text-white"
                            : "bg-nonna-warm/50 text-nonna-brown/70 hover:bg-nonna-warm"
                        }`}
                      >
                        {person}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {(activeTags.length > 0 || activePeople.length > 0) && (
                <button
                  onClick={() => { setActiveTags([]); setActivePeople([]); }}
                  className="text-sm text-nonna-accent hover:underline"
                >
                  Clear all filters
                </button>
              )}
            </div>
          )}

          {/* Active filter chips */}
          {(activeTags.length > 0 || activePeople.length > 0) && !showFilters && (
            <div className="flex flex-wrap gap-2 mt-2">
              {activeTags.map((tag) => (
                <span
                  key={tag}
                  className="text-xs bg-nonna-accent/10 text-nonna-accent px-3 py-1 rounded-full flex items-center gap-1"
                >
                  {tagDisplayName[tag] || tag}
                  <button onClick={() => setActiveTags((p) => p.filter((t) => t !== tag))}>&times;</button>
                </span>
              ))}
              {activePeople.map((p) => (
                <span
                  key={p}
                  className="text-xs bg-nonna-accent/10 text-nonna-accent px-3 py-1 rounded-full flex items-center gap-1"
                >
                  {p}
                  <button onClick={() => setActivePeople((prev) => prev.filter((x) => x !== p))}>&times;</button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Search Results */}
        {searchResults !== null ? (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <p className="text-nonna-brown/60">
                {searchResults.length} result{searchResults.length !== 1 ? "s" : ""}
                {searchQuery && ` for "${searchQuery}"`}
              </p>
              <button
                onClick={() => { setSearchQuery(""); setSearchResults(null); setActiveTags([]); setActivePeople([]); }}
                className="text-sm text-nonna-accent hover:underline"
              >
                Clear search
              </button>
            </div>
            {searchResults.length === 0 ? (
              <p className="text-center py-12 text-nonna-brown/40">
                No stories match your search. Try different keywords.
              </p>
            ) : (
              <div className="space-y-4">
                {searchResults.map((r) => (
                  <div key={`${r.session_id}-${r.moment_id}`} className="bg-white rounded-2xl p-5 shadow-sm flex gap-4">
                    {r.image_url && (
                      <img src={r.image_url} alt="" className="w-32 h-24 rounded-xl object-cover flex-shrink-0" />
                    )}
                    <div className="flex-1">
                      <h3 className="font-bold text-lg">{r.title}</h3>
                      <p className="text-nonna-brown/80 text-sm mb-1">{r.summary}</p>
                      {r.quote && (
                        <p className="text-sm italic text-nonna-brown/60 mb-2">&ldquo;{r.quote}&rdquo;</p>
                      )}
                      <div className="flex flex-wrap gap-1">
                        {r.tags.map((tag) => (
                          <span key={tag} className="text-xs bg-nonna-warm/50 text-nonna-brown/60 px-2 py-0.5 rounded-full">
                            {tagDisplayName[tag] || tag}
                          </span>
                        ))}
                        {r.people_mentioned.map((p) => (
                          <span key={p} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                            {p}
                          </span>
                        ))}
                        <span className="text-xs text-nonna-brown/40">
                          {new Date(r.session_date).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <>
            {/* Tab Navigation */}
            <div className="flex gap-1 mb-8 bg-nonna-warm/30 rounded-xl p-1">
              {(["timeline", "people", "themes", "collections"] as ViewTab[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 py-3 rounded-lg text-center capitalize font-semibold transition-colors ${
                    activeTab === tab
                      ? "bg-white text-nonna-dark shadow-sm"
                      : "text-nonna-brown/60 hover:text-nonna-dark"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Timeline View */}
            {activeTab === "timeline" && (
              sessions.length === 0 ? (
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
                                   selectedSession === session.id ? "ring-2 ring-nonna-accent" : ""
                                 }`}
                    >
                      <div className="flex items-center gap-3 mb-3">
                        <span className="text-2xl">
                          {session.channel === "phone" ? "\u{1F4DE}" : "\u{1F4F9}"}
                        </span>
                        <span className="text-sm text-nonna-brown/50">
                          {new Date(session.started_at).toLocaleDateString("en-US", {
                            weekday: "long", month: "long", day: "numeric",
                          })}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mb-2">
                        {session.status === "complete" && (
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">Reel Ready</span>
                        )}
                        {session.status === "processing" && (
                          <span className="text-xs bg-nonna-warm text-nonna-brown px-2 py-1 rounded-full">Creating Reel...</span>
                        )}
                        {session.status === "live" && (
                          <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full animate-pulse">Live Now</span>
                        )}
                        {session.duration && (
                          <span className="text-xs text-nonna-brown/40">{Math.round(session.duration / 60)} min</span>
                        )}
                      </div>
                      {session.topics_covered.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {session.topics_covered.slice(0, 4).map((topic) => (
                            <span key={topic} className="text-xs bg-nonna-warm/50 text-nonna-brown/70 px-2 py-1 rounded-full">
                              {topic}
                            </span>
                          ))}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )
            )}

            {/* People View */}
            {activeTab === "people" && (
              personThreads.length === 0 ? (
                <p className="text-center py-12 text-nonna-brown/40">
                  People threads will appear after multiple conversations mention the same person.
                </p>
              ) : (
                <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6">
                  {personThreads.map((thread) => (
                    <button
                      key={thread.id}
                      onClick={() => {
                        setSearchQuery("");
                        setActivePeople([thread.name]);
                        setActiveTags([]);
                      }}
                      className="bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow text-left"
                    >
                      <div className="w-12 h-12 rounded-full bg-nonna-warm flex items-center justify-center text-xl mb-3">
                        {thread.name[0]}
                      </div>
                      <h3 className="font-bold text-lg">{thread.name}</h3>
                      <p className="text-sm text-nonna-brown/50">
                        {thread.moment_refs.length} stories across {thread.session_count} conversations
                      </p>
                    </button>
                  ))}
                </div>
              )
            )}

            {/* Themes View */}
            {activeTab === "themes" && (
              themeThreads.length === 0 ? (
                <p className="text-center py-12 text-nonna-brown/40">
                  Theme threads will appear after stories are tagged across multiple conversations.
                </p>
              ) : (
                <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6">
                  {themeThreads.map((thread) => (
                    <button
                      key={thread.id}
                      onClick={() => {
                        setSearchQuery("");
                        setActiveTags([thread.name.toLowerCase().replace(/ /g, "_")]);
                        setActivePeople([]);
                      }}
                      className="bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow text-left"
                    >
                      <h3 className="font-bold text-lg mb-1">{thread.name}</h3>
                      <p className="text-sm text-nonna-brown/50">
                        {thread.moment_refs.length} moments across {thread.session_count} conversations
                      </p>
                    </button>
                  ))}
                  {/* Also show place threads */}
                  {placeThreads.map((thread) => (
                    <button
                      key={thread.id}
                      onClick={() => {
                        setSearchQuery(thread.name.replace("Stories from ", ""));
                        setActiveTags([]);
                        setActivePeople([]);
                      }}
                      className="bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow text-left"
                    >
                      <h3 className="font-bold text-lg mb-1">{thread.name}</h3>
                      <p className="text-sm text-nonna-brown/50">
                        {thread.moment_refs.length} moments across {thread.session_count} conversations
                      </p>
                    </button>
                  ))}
                </div>
              )
            )}

            {/* Collections View */}
            {activeTab === "collections" && (
              <div>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-semibold">Collections</h2>
                  <Link
                    href={`/family/${familyId}/collections`}
                    className="text-nonna-accent hover:underline text-sm"
                  >
                    Manage Collections
                  </Link>
                </div>
                {collections.length === 0 ? (
                  <p className="text-center py-12 text-nonna-brown/40">
                    No collections yet. Create one to curate your favorite moments.
                  </p>
                ) : (
                  <div className="grid sm:grid-cols-2 gap-6">
                    {collections.map((coll) => (
                      <Link
                        key={coll.id}
                        href={`/family/${familyId}/collections?id=${coll.id}`}
                        className="bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow"
                      >
                        {coll.cover_image_url && (
                          <img src={coll.cover_image_url} alt="" className="w-full h-40 rounded-xl object-cover mb-4" />
                        )}
                        <h3 className="font-bold text-lg">{coll.name}</h3>
                        {coll.description && (
                          <p className="text-sm text-nonna-brown/60 mt-1">{coll.description}</p>
                        )}
                        <p className="text-xs text-nonna-brown/40 mt-2">
                          {coll.moment_refs.length} moment{coll.moment_refs.length !== 1 ? "s" : ""}
                        </p>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* Selected Session Detail */}
        {selected && !searchResults && (
          <div className="mt-12 space-y-8">
            <h2 className="text-2xl font-serif font-bold">
              {new Date(selected.started_at).toLocaleDateString("en-US", {
                weekday: "long", month: "long", day: "numeric", year: "numeric",
              })}
            </h2>

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
                <p className="text-xl text-nonna-brown/60">Nonna is crafting this memory...</p>
                <p className="text-nonna-brown/40 mt-2">The Memory Reel will appear here when it&apos;s ready.</p>
              </div>
            )}

            {selected.moments && selected.moments.length > 0 && (
              <div className="space-y-6">
                <h3 className="text-xl font-semibold">Story Moments</h3>
                {selected.moments.map((moment) => (
                  <div
                    key={moment.id}
                    className="bg-white rounded-2xl p-6 shadow-sm cursor-pointer hover:shadow-md transition-shadow"
                    onClick={() => setSelectedMoment(selectedMoment?.id === moment.id ? null : moment)}
                  >
                    <div className="flex gap-6">
                      {moment.image_url && (
                        <img src={moment.image_url} alt={moment.title} className="w-40 h-28 rounded-xl object-cover flex-shrink-0" />
                      )}
                      <div className="flex-1">
                        <h4 className="font-bold text-lg mb-1">{moment.title}</h4>
                        <p className="text-nonna-brown/80 mb-2">{moment.summary}</p>
                        {moment.quote && (
                          <blockquote className="italic text-nonna-brown/60 border-l-2 border-nonna-gold pl-3">
                            &ldquo;{moment.quote}&rdquo;
                          </blockquote>
                        )}
                        <div className="flex flex-wrap gap-1 mt-2 items-center">
                          <span className="text-xs bg-nonna-warm/50 text-nonna-brown/60 px-2 py-1 rounded-full capitalize">
                            {moment.emotional_tone}
                          </span>
                          {moment.tags.map((tag) => (
                            <span key={tag} className="text-xs bg-nonna-warm/50 text-nonna-brown/60 px-2 py-1 rounded-full">
                              {tagDisplayName[tag] || tag}
                            </span>
                          ))}
                          {moment.people_mentioned.map((p) => (
                            <span key={p} className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-full">
                              {p}
                            </span>
                          ))}
                          {collections.length > 0 && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setAddToCollectionMoment(
                                  addToCollectionMoment?.momentId === moment.id
                                    ? null
                                    : { sessionId: selected!.id, momentId: moment.id }
                                );
                              }}
                              className="ml-auto text-xs text-nonna-accent hover:underline flex items-center gap-1"
                            >
                              + Collection
                            </button>
                          )}
                        </div>
                        {/* Collection picker dropdown */}
                        {addToCollectionMoment?.momentId === moment.id && (
                          <div className="mt-2 bg-nonna-warm/20 rounded-lg p-3 space-y-1">
                            <p className="text-xs font-semibold text-nonna-brown/60 mb-1">Add to:</p>
                            {collections.map((coll) => (
                              <button
                                key={coll.id}
                                onClick={(e) => { e.stopPropagation(); handleAddToCollection(coll.id); }}
                                className="block w-full text-left text-sm px-3 py-2 rounded-lg hover:bg-white transition-colors"
                              >
                                {coll.name}
                                <span className="text-xs text-nonna-brown/40 ml-2">
                                  ({coll.moment_refs.length} moments)
                                </span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Expanded detail */}
                    {selectedMoment?.id === moment.id && (
                      <div className="mt-4 pt-4 border-t border-nonna-warm/30 space-y-3">
                        {moment.people_mentioned.length > 0 && (
                          <div>
                            <p className="text-sm font-semibold text-nonna-brown/60">People mentioned</p>
                            <div className="flex gap-2 mt-1">
                              {moment.people_mentioned.map((p) => (
                                <button
                                  key={p}
                                  onClick={(e) => { e.stopPropagation(); setActivePeople([p]); setSearchResults(null); }}
                                  className="text-sm text-nonna-accent hover:underline"
                                >
                                  {p}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                        {moment.place_mentioned && (
                          <p className="text-sm text-nonna-brown/60">
                            <span className="font-semibold">Place: </span>{moment.place_mentioned}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Toast notification */}
      {collectionToast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-nonna-dark text-white px-6 py-3 rounded-xl shadow-lg z-50 animate-fade-in">
          {collectionToast}
        </div>
      )}
    </main>
  );
}
