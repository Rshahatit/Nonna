"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { api, setTokenProvider, type Collection, type Family, type Moment } from "@/lib/api";
import { NavHeader } from "@/components/NavHeader";

export default function CollectionsPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const familyId = params.familyId as string;
  const selectedId = searchParams.get("id");
  const { user, loading: authLoading, getToken } = useAuth();

  const [family, setFamily] = useState<Family | null>(null);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<Collection | null>(null);
  const [collectionMoments, setCollectionMoments] = useState<Moment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!user) { router.push("/"); return; }
    setTokenProvider(getToken);

    async function load() {
      try {
        const [familyData, collData] = await Promise.all([
          api.getFamily(familyId),
          api.listCollections(familyId),
        ]);
        setFamily(familyData);
        setCollections(collData);

        if (selectedId) {
          const coll = collData.find((c) => c.id === selectedId);
          if (coll) {
            setSelectedCollection(coll);
            await loadCollectionMoments(coll);
          }
        }
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user, authLoading, familyId, selectedId, getToken, router]);

  const loadCollectionMoments = async (coll: Collection) => {
    const moments: Moment[] = [];
    for (const ref of coll.moment_refs) {
      try {
        const sessionMoments = await api.getMoments(ref.session_id);
        const match = sessionMoments.find((m) => m.id === ref.moment_id);
        if (match) moments.push(match);
      } catch {
        // ignore
      }
    }
    setCollectionMoments(moments);
  };

  const handleCreate = async () => {
    if (!newName.trim() || !family) return;
    setCreating(true);
    try {
      const coll = await api.createCollection(familyId, {
        name: newName,
        description: newDesc,
        elder_id: family.elder_ids[0] || "",
      });
      setCollections((prev) => [coll, ...prev]);
      setNewName("");
      setNewDesc("");
    } catch {
      alert("Failed to create collection");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (collId: string) => {
    if (!confirm("Delete this collection?")) return;
    try {
      await api.deleteCollection(familyId, collId);
      setCollections((prev) => prev.filter((c) => c.id !== collId));
      if (selectedCollection?.id === collId) {
        setSelectedCollection(null);
        setCollectionMoments([]);
      }
    } catch {
      alert("Failed to delete collection");
    }
  };

  if (authLoading || loading) {
    return <main className="min-h-screen flex items-center justify-center"><p className="text-xl text-nonna-brown/60">Loading...</p></main>;
  }

  return (
    <main className="min-h-screen">
      <NavHeader familyName={family?.name} />

      <div className="max-w-4xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-serif font-bold mb-8">Collections</h1>

        {/* Create new */}
        <div className="bg-white rounded-xl p-6 shadow-sm mb-8 space-y-3">
          <h2 className="font-bold text-lg">New Collection</h2>
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Collection name (e.g., Grandma's Kitchen)"
            className="w-full p-3 rounded-lg border border-nonna-warm"
          />
          <input
            type="text"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            placeholder="Description (optional)"
            className="w-full p-3 rounded-lg border border-nonna-warm"
          />
          <button
            onClick={handleCreate}
            disabled={!newName.trim() || creating}
            className="bg-nonna-accent text-white px-6 py-3 rounded-lg font-semibold
                       hover:bg-nonna-brown transition-colors disabled:opacity-50"
          >
            {creating ? "Creating..." : "Create Collection"}
          </button>
        </div>

        {/* Collection list */}
        {collections.length === 0 ? (
          <p className="text-center py-12 text-nonna-brown/40">
            No collections yet. Create one to curate your favorite moments.
          </p>
        ) : (
          <div className="space-y-4">
            {collections.map((coll) => (
              <div
                key={coll.id}
                className={`bg-white rounded-xl p-6 shadow-sm cursor-pointer hover:shadow-md transition-shadow ${
                  selectedCollection?.id === coll.id ? "ring-2 ring-nonna-accent" : ""
                }`}
                onClick={async () => {
                  setSelectedCollection(coll);
                  await loadCollectionMoments(coll);
                }}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-bold text-lg">{coll.name}</h3>
                    {coll.description && <p className="text-sm text-nonna-brown/60">{coll.description}</p>}
                    <p className="text-xs text-nonna-brown/40 mt-1">
                      {coll.moment_refs.length} moment{coll.moment_refs.length !== 1 ? "s" : ""}
                      {coll.is_public && " · Public"}
                    </p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(coll.id); }}
                    className="text-sm text-red-400 hover:text-red-600"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Selected collection moments */}
        {selectedCollection && (
          <div className="mt-8 space-y-4">
            <h2 className="text-xl font-bold">{selectedCollection.name}</h2>
            {collectionMoments.length === 0 ? (
              <p className="text-nonna-brown/40">
                No moments in this collection yet. Add moments from the archive.
              </p>
            ) : (
              <div className="space-y-4">
                {collectionMoments.map((moment) => (
                  <div key={moment.id} className="bg-white rounded-xl p-5 shadow-sm flex gap-4">
                    {moment.image_url && (
                      <img src={moment.image_url} alt="" className="w-32 h-24 rounded-lg object-cover flex-shrink-0" />
                    )}
                    <div>
                      <h4 className="font-bold">{moment.title}</h4>
                      <p className="text-sm text-nonna-brown/80">{moment.summary}</p>
                      {moment.quote && (
                        <p className="text-sm italic text-nonna-brown/60 mt-1">&ldquo;{moment.quote}&rdquo;</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
