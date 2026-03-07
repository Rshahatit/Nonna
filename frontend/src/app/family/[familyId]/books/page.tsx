"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import {
  api, setTokenProvider,
  type Family, type Book, type Session, type Collection,
} from "@/lib/api";
import { NavHeader } from "@/components/NavHeader";

export default function BooksPage() {
  const params = useParams();
  const router = useRouter();
  const familyId = params.familyId as string;
  const { user, loading: authLoading, getToken } = useAuth();

  const [family, setFamily] = useState<Family | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);

  // Book creation form
  const [title, setTitle] = useState("");
  const [sourceType, setSourceType] = useState<"sessions" | "collection">("sessions");
  const [selectedSessions, setSelectedSessions] = useState<string[]>([]);
  const [selectedCollection, setSelectedCollection] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!user) { router.push("/"); return; }
    setTokenProvider(getToken);

    async function load() {
      try {
        const [familyData, bookData] = await Promise.all([
          api.getFamily(familyId),
          api.listBooks(familyId),
        ]);
        setFamily(familyData);
        setBooks(bookData);

        if (familyData.elder_ids[0]) {
          const [sessionData, collData] = await Promise.all([
            api.listSessions(familyData.elder_ids[0]),
            api.listCollections(familyId).catch(() => []),
          ]);
          setSessions(sessionData.filter((s) => s.status === "complete"));
          setCollections(collData);
        }
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user, authLoading, familyId, getToken, router]);

  const handleCreate = async () => {
    if (!title.trim() || !family?.elder_ids[0]) return;
    setCreating(true);

    const sourceIds = sourceType === "sessions" ? selectedSessions : [selectedCollection];

    try {
      const book = await api.createBook(familyId, {
        title,
        elder_id: family.elder_ids[0],
        source_type: sourceType,
        source_ids: sourceIds,
      });
      setBooks((prev) => [book, ...prev]);
      setTitle("");
      setSelectedSessions([]);
      setSelectedCollection("");
    } catch {
      alert("Failed to create book");
    } finally {
      setCreating(false);
    }
  };

  const statusLabel: Record<string, string> = {
    generating: "Nonna is assembling your book...",
    preview_ready: "Preview Ready",
    ordered: "Order Placed",
    shipped: "Shipped",
  };

  if (authLoading || loading) {
    return <main className="min-h-screen flex items-center justify-center"><p className="text-xl text-nonna-brown/60">Loading...</p></main>;
  }

  return (
    <main className="min-h-screen">
      <NavHeader familyName={family?.name} />

      <div className="max-w-4xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-serif font-bold mb-2">Keepsake Books</h1>
        <p className="text-nonna-brown/60 mb-8">
          Turn conversations into a beautiful printed book with illustrations, quotes, and QR codes linking to video reels.
        </p>

        {/* Create book form */}
        <div className="bg-white rounded-xl p-6 shadow-sm mb-8 space-y-4">
          <h2 className="font-bold text-lg">Create a New Book</h2>

          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Book title (e.g., Stories from Grandma Maria)"
            className="w-full p-3 rounded-lg border border-nonna-warm"
          />

          <div>
            <p className="text-sm font-semibold mb-2">Source</p>
            <div className="flex gap-3">
              <button
                onClick={() => setSourceType("sessions")}
                className={`px-4 py-2 rounded-lg text-sm ${
                  sourceType === "sessions"
                    ? "bg-nonna-accent text-white"
                    : "border border-nonna-warm text-nonna-brown/60"
                }`}
              >
                Select Sessions
              </button>
              <button
                onClick={() => setSourceType("collection")}
                className={`px-4 py-2 rounded-lg text-sm ${
                  sourceType === "collection"
                    ? "bg-nonna-accent text-white"
                    : "border border-nonna-warm text-nonna-brown/60"
                }`}
              >
                From Collection
              </button>
            </div>
          </div>

          {sourceType === "sessions" && (
            <div className="max-h-48 overflow-y-auto space-y-2">
              {sessions.map((s) => (
                <label key={s.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedSessions.includes(s.id)}
                    onChange={(e) =>
                      setSelectedSessions((prev) =>
                        e.target.checked ? [...prev, s.id] : prev.filter((id) => id !== s.id)
                      )
                    }
                    className="accent-nonna-accent"
                  />
                  {new Date(s.started_at).toLocaleDateString("en-US", {
                    weekday: "short", month: "short", day: "numeric",
                  })}
                  {s.topics_covered.length > 0 && (
                    <span className="text-nonna-brown/40">— {s.topics_covered.slice(0, 2).join(", ")}</span>
                  )}
                </label>
              ))}
              {sessions.length === 0 && (
                <p className="text-sm text-nonna-brown/40">No completed sessions yet.</p>
              )}
            </div>
          )}

          {sourceType === "collection" && (
            <select
              value={selectedCollection}
              onChange={(e) => setSelectedCollection(e.target.value)}
              className="w-full p-3 rounded-lg border border-nonna-warm"
            >
              <option value="">Select a collection</option>
              {collections.map((c) => (
                <option key={c.id} value={c.id}>{c.name} ({c.moment_refs.length} moments)</option>
              ))}
            </select>
          )}

          <button
            onClick={handleCreate}
            disabled={creating || !title.trim() ||
              (sourceType === "sessions" && selectedSessions.length === 0) ||
              (sourceType === "collection" && !selectedCollection)}
            className="bg-nonna-accent text-white px-6 py-3 rounded-lg font-semibold
                       hover:bg-nonna-brown transition-colors disabled:opacity-50"
          >
            {creating ? "Creating..." : "Generate Book"}
          </button>
        </div>

        {/* Book list */}
        <h2 className="text-xl font-bold mb-4">Your Books</h2>
        {books.length === 0 ? (
          <p className="text-center py-12 text-nonna-brown/40">
            No books yet. Create your first keepsake book above.
          </p>
        ) : (
          <div className="space-y-4">
            {books.map((book) => (
              <div key={book.id} className="bg-white rounded-xl p-6 shadow-sm">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-bold text-lg">{book.title}</h3>
                    <p className="text-sm text-nonna-brown/50">
                      {book.page_count > 0 ? `${book.page_count} pages · ` : ""}
                      {statusLabel[book.status] || book.status}
                    </p>
                    <p className="text-xs text-nonna-brown/40 mt-1">
                      Created {new Date(book.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {book.status === "generating" && (
                      <span className="text-xs bg-yellow-100 text-yellow-700 px-3 py-1 rounded-full animate-pulse">
                        Generating...
                      </span>
                    )}
                    {book.status === "preview_ready" && book.pdf_url && (
                      <a
                        href={book.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm bg-nonna-accent text-white px-4 py-2 rounded-lg hover:bg-nonna-brown transition-colors"
                      >
                        Download PDF
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
