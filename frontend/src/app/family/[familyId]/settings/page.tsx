"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { api, setTokenProvider, type Family, type FamilyMember, type Invite } from "@/lib/api";
import { NavHeader } from "@/components/NavHeader";

export default function FamilySettingsPage() {
  const params = useParams();
  const router = useRouter();
  const familyId = params.familyId as string;
  const { user, loading: authLoading, getToken } = useAuth();

  const [family, setFamily] = useState<Family | null>(null);
  const [members, setMembers] = useState<FamilyMember[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteRole, setInviteRole] = useState<"member" | "viewer">("member");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteLink, setInviteLink] = useState("");

  useEffect(() => {
    if (authLoading) return;
    if (!user) { router.push("/"); return; }
    setTokenProvider(getToken);

    async function load() {
      try {
        const [familyData, memberData, inviteData] = await Promise.all([
          api.getFamily(familyId),
          api.listMembers(familyId),
          api.listInvites(familyId).catch(() => []),
        ]);
        setFamily(familyData);
        setMembers(memberData);
        setInvites(inviteData);
      } catch {
        // May not have access
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user, authLoading, familyId, getToken, router]);

  const handleCreateInvite = async () => {
    try {
      const invite = await api.createInvite(familyId, {
        email: inviteEmail || undefined,
        role: inviteRole,
      });
      const baseUrl = typeof window !== "undefined" ? window.location.origin : "";
      setInviteLink(`${baseUrl}/invite/${invite.token}`);
      setInvites((prev) => [invite, ...prev]);
      setInviteEmail("");
    } catch {
      alert("Failed to create invite");
    }
  };

  const handleRevokeInvite = async (inviteId: string) => {
    try {
      await api.revokeInvite(familyId, inviteId);
      setInvites((prev) => prev.map((i) => i.id === inviteId ? { ...i, status: "expired" as const } : i));
    } catch {
      // ignore
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!confirm("Remove this member from the family?")) return;
    try {
      await api.removeMember(familyId, userId);
      setMembers((prev) => prev.filter((m) => m.user_id !== userId));
    } catch {
      alert("Failed to remove member");
    }
  };

  const handleRoleChange = async (userId: string, role: string) => {
    try {
      await api.updateMember(familyId, userId, { role } as any);
      setMembers((prev) => prev.map((m) => m.user_id === userId ? { ...m, role: role as any } : m));
    } catch {
      alert("Failed to update role");
    }
  };

  if (authLoading || loading) {
    return <main className="min-h-screen flex items-center justify-center"><p className="text-xl text-nonna-brown/60">Loading...</p></main>;
  }

  if (!family) {
    return <main className="min-h-screen flex items-center justify-center"><p className="text-xl text-red-600">Family not found</p></main>;
  }

  const currentMember = members.find((m) => m.user_id === user?.uid);
  const isOrganizer = currentMember?.role === "organizer";

  return (
    <main className="min-h-screen">
      <NavHeader familyName={family.name} />

      <div className="max-w-3xl mx-auto px-6 py-12 space-y-12">
        <h1 className="text-3xl font-serif font-bold">Family Settings</h1>

        {/* Members */}
        <section>
          <h2 className="text-xl font-bold mb-4">Members ({members.length})</h2>
          <div className="space-y-3">
            {members.map((member) => (
              <div key={member.user_id} className="flex items-center justify-between bg-white rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-3">
                  {member.photo_url && (
                    <img src={member.photo_url} alt="" className="w-10 h-10 rounded-full" referrerPolicy="no-referrer" />
                  )}
                  <div>
                    <p className="font-semibold">{member.name || member.email}</p>
                    <p className="text-sm text-nonna-brown/50">{member.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {isOrganizer && member.user_id !== user?.uid ? (
                    <>
                      <select
                        value={member.role}
                        onChange={(e) => handleRoleChange(member.user_id, e.target.value)}
                        className="text-sm border border-nonna-warm rounded-lg px-2 py-1"
                      >
                        <option value="organizer">Organizer</option>
                        <option value="member">Member</option>
                        <option value="viewer">Viewer</option>
                      </select>
                      <button
                        onClick={() => handleRemoveMember(member.user_id)}
                        className="text-sm text-red-500 hover:underline"
                      >
                        Remove
                      </button>
                    </>
                  ) : (
                    <span className="text-sm text-nonna-brown/50 capitalize bg-nonna-warm/30 px-3 py-1 rounded-full">
                      {member.role}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Invite */}
        {isOrganizer && (
          <section>
            <h2 className="text-xl font-bold mb-4">Invite Family Members</h2>
            <div className="bg-white rounded-xl p-6 shadow-sm space-y-4">
              <div className="flex gap-3">
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="Email (optional)"
                  className="flex-1 p-3 rounded-lg border border-nonna-warm"
                />
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as "member" | "viewer")}
                  className="p-3 rounded-lg border border-nonna-warm"
                >
                  <option value="member">Member</option>
                  <option value="viewer">Viewer</option>
                </select>
                <button
                  onClick={handleCreateInvite}
                  className="bg-nonna-accent text-white px-6 py-3 rounded-lg font-semibold hover:bg-nonna-brown transition-colors"
                >
                  Create Invite
                </button>
              </div>

              {inviteLink && (
                <div className="bg-green-50 p-4 rounded-lg">
                  <p className="text-sm font-semibold text-green-800 mb-1">Invite link created!</p>
                  <p className="text-sm text-green-700 break-all">{inviteLink}</p>
                  <button
                    onClick={() => { navigator.clipboard.writeText(inviteLink); }}
                    className="text-sm text-green-600 hover:underline mt-1"
                  >
                    Copy to clipboard
                  </button>
                </div>
              )}
            </div>

            {/* Pending invites */}
            {invites.filter((i) => i.status === "pending").length > 0 && (
              <div className="mt-4 space-y-2">
                <h3 className="text-sm font-semibold text-nonna-brown/60">Pending Invites</h3>
                {invites.filter((i) => i.status === "pending").map((invite) => (
                  <div key={invite.id} className="flex items-center justify-between bg-nonna-warm/20 rounded-lg p-3">
                    <div className="text-sm">
                      {invite.email || "Link invite"} — <span className="capitalize">{invite.role}</span>
                    </div>
                    <button
                      onClick={() => handleRevokeInvite(invite.id)}
                      className="text-sm text-red-500 hover:underline"
                    >
                      Revoke
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Notification Preferences */}
        <section>
          <h2 className="text-xl font-bold mb-4">Your Notification Preferences</h2>
          {currentMember && (
            <div className="bg-white rounded-xl p-6 shadow-sm space-y-4">
              {[
                { key: "reel_ready", label: "New Memory Reel ready" },
                { key: "missed_calls", label: "Missed scheduled calls" },
                { key: "weekly_digest", label: "Weekly digest email" },
              ].map(({ key, label }) => (
                <label key={key} className="flex items-center justify-between">
                  <span>{label}</span>
                  <input
                    type="checkbox"
                    checked={(currentMember.notification_prefs as any)[key]}
                    onChange={async (e) => {
                      const newPrefs = { ...currentMember.notification_prefs, [key]: e.target.checked };
                      try {
                        await api.updateMember(familyId, currentMember.user_id, {
                          notification_prefs: newPrefs,
                        } as any);
                        setMembers((prev) => prev.map((m) =>
                          m.user_id === currentMember.user_id
                            ? { ...m, notification_prefs: newPrefs }
                            : m
                        ));
                      } catch { /* ignore */ }
                    }}
                    className="w-5 h-5 accent-nonna-accent"
                  />
                </label>
              ))}
              <div className="flex items-center justify-between">
                <span>Notification channel</span>
                <select
                  value={currentMember.notification_prefs.channel}
                  onChange={async (e) => {
                    const newPrefs = { ...currentMember.notification_prefs, channel: e.target.value as any };
                    try {
                      await api.updateMember(familyId, currentMember.user_id, {
                        notification_prefs: newPrefs,
                      } as any);
                      setMembers((prev) => prev.map((m) =>
                        m.user_id === currentMember.user_id
                          ? { ...m, notification_prefs: newPrefs }
                          : m
                      ));
                    } catch { /* ignore */ }
                  }}
                  className="p-2 rounded-lg border border-nonna-warm"
                >
                  <option value="email">Email</option>
                  <option value="sms">SMS</option>
                  <option value="both">Both</option>
                </select>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
