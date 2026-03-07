"use client";

import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export function NavHeader({ familyName }: { familyName?: string }) {
  const { user, logOut } = useAuth();

  return (
    <nav className="flex items-center justify-between px-6 py-4 border-b border-nonna-warm/50">
      <div className="flex items-center gap-3">
        <Link href="/dashboard" className="text-2xl font-serif font-bold hover:text-nonna-accent">
          Nonna
        </Link>
        {familyName && (
          <>
            <span className="text-nonna-brown/30">/</span>
            <span className="text-lg text-nonna-brown/70">{familyName}</span>
          </>
        )}
      </div>
      <div className="flex items-center gap-4">
        {user && (
          <>
            {user.photoURL && (
              <img
                src={user.photoURL}
                alt=""
                className="w-8 h-8 rounded-full"
                referrerPolicy="no-referrer"
              />
            )}
            <span className="text-sm text-nonna-brown/60 hidden sm:block">
              {user.displayName || user.email}
            </span>
            <button
              onClick={logOut}
              className="text-sm text-nonna-brown/50 hover:text-nonna-accent"
            >
              Sign Out
            </button>
          </>
        )}
      </div>
    </nav>
  );
}
