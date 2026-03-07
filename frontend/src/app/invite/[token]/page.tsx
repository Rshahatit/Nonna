"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { api, setTokenProvider, type Invite } from "@/lib/api";

export default function InvitePage() {
  const params = useParams();
  const router = useRouter();
  const token = params.token as string;
  const { user, loading: authLoading, signIn, getToken } = useAuth();

  const [invite, setInvite] = useState<Invite | null>(null);
  const [loading, setLoading] = useState(true);
  const [redeeming, setRedeeming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const inv = await api.getInvite(token);
        setInvite(inv);
      } catch {
        setError("This invite link is invalid or has expired.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [token]);

  const handleJoin = async () => {
    if (!user) {
      try {
        await signIn();
      } catch {
        return;
      }
    }

    setRedeeming(true);
    setTokenProvider(getToken);

    try {
      await api.signIn();
      await api.redeemInvite(token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to join");
    } finally {
      setRedeeming(false);
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <p className="text-xl text-nonna-brown/60">Loading invite...</p>
      </main>
    );
  }

  if (error || !invite) {
    return (
      <main className="min-h-screen flex items-center justify-center px-6">
        <div className="text-center space-y-4 max-w-md">
          <h1 className="text-3xl font-serif font-bold">Invite Not Found</h1>
          <p className="text-nonna-brown/60">{error || "This invite link is invalid."}</p>
          <a href="/" className="text-nonna-accent hover:underline">Go to Nonna</a>
        </div>
      </main>
    );
  }

  if (invite.status !== "pending") {
    return (
      <main className="min-h-screen flex items-center justify-center px-6">
        <div className="text-center space-y-4 max-w-md">
          <h1 className="text-3xl font-serif font-bold">Invite {invite.status === "redeemed" ? "Already Used" : "Expired"}</h1>
          <p className="text-nonna-brown/60">
            {invite.status === "redeemed"
              ? "This invite has already been redeemed."
              : "This invite has expired. Ask your family member for a new link."}
          </p>
          <a href="/dashboard" className="text-nonna-accent hover:underline">Go to Dashboard</a>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-6">
      <div className="text-center space-y-6 max-w-md">
        <h1 className="text-4xl font-serif font-bold">You&apos;re Invited!</h1>
        <p className="text-xl text-nonna-brown/80">
          <strong>{invite.inviter_name || "A family member"}</strong> invited you to join
        </p>
        <p className="text-2xl font-serif font-bold text-nonna-accent">
          {invite.family_name}
        </p>
        <p className="text-nonna-brown/60">
          As a <span className="capitalize font-semibold">{invite.role}</span>, you&apos;ll be able to{" "}
          {invite.role === "member"
            ? "browse the archive, create collections, and more."
            : "view the family archive and Memory Reels."}
        </p>
        <button
          onClick={handleJoin}
          disabled={redeeming}
          className="w-full bg-nonna-accent text-white text-xl font-semibold
                     py-4 rounded-xl hover:bg-nonna-brown transition-colors
                     disabled:opacity-50"
        >
          {redeeming ? "Joining..." : user ? "Join Family" : "Sign in with Google & Join"}
        </button>
      </div>
    </main>
  );
}
