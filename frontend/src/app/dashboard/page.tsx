"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { api, setTokenProvider, type Family, type Elder } from "@/lib/api";
import { NavHeader } from "@/components/NavHeader";

export default function DashboardPage() {
  const { user, loading: authLoading, signIn, getToken } = useAuth();
  const router = useRouter();
  const [families, setFamilies] = useState<Family[]>([]);
  const [elders, setElders] = useState<Record<string, Elder>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/");
      return;
    }

    setTokenProvider(getToken);

    async function load() {
      try {
        await api.signIn();
        const fams = await api.getMyFamilies();
        setFamilies(fams);

        // If only one family, redirect directly
        if (fams.length === 1 && fams[0].elder_ids.length > 0) {
          router.push(`/family/${fams[0].id}/archive/${fams[0].elder_ids[0]}`);
          return;
        }

        // Load elder names
        const elderMap: Record<string, Elder> = {};
        for (const fam of fams) {
          for (const eid of fam.elder_ids) {
            try {
              elderMap[eid] = await api.getElder(eid);
            } catch {
              // Elder might not exist
            }
          }
        }
        setElders(elderMap);
      } catch {
        // May not have families yet
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user, authLoading, getToken, router]);

  if (authLoading || loading) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <p className="text-xl text-nonna-brown/60">Loading...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen">
      <NavHeader />

      <div className="max-w-4xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-serif font-bold mb-8">Your Families</h1>

        {families.length === 0 ? (
          <div className="text-center py-20 bg-white/50 rounded-2xl">
            <p className="text-xl text-nonna-brown/60 mb-4">
              You haven&apos;t joined any families yet.
            </p>
            <p className="text-nonna-brown/40 mb-8">
              Set up Nonna for your family to get started, or join with an invite link.
            </p>
            <Link
              href="/setup"
              className="bg-nonna-accent text-white text-lg font-semibold
                         px-8 py-4 rounded-xl hover:bg-nonna-brown transition-colors"
            >
              Set Up Nonna
            </Link>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-6">
            {families.map((family) => (
              <div
                key={family.id}
                className="bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow"
              >
                <h2 className="text-xl font-bold mb-3">{family.name}</h2>
                <div className="space-y-2 mb-4">
                  {family.elder_ids.map((eid) => {
                    const elder = elders[eid];
                    return (
                      <Link
                        key={eid}
                        href={`/family/${family.id}/archive/${eid}`}
                        className="block text-nonna-accent hover:underline"
                      >
                        {elder?.name || "Elder"}&apos;s Stories
                      </Link>
                    );
                  })}
                </div>
                <div className="flex gap-3">
                  <Link
                    href={`/family/${family.id}/settings`}
                    className="text-sm text-nonna-brown/50 hover:text-nonna-accent"
                  >
                    Settings
                  </Link>
                  <Link
                    href={`/family/${family.id}/collections`}
                    className="text-sm text-nonna-brown/50 hover:text-nonna-accent"
                  >
                    Collections
                  </Link>
                  <Link
                    href={`/family/${family.id}/books`}
                    className="text-sm text-nonna-brown/50 hover:text-nonna-accent"
                  >
                    Books
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
