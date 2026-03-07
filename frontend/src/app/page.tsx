"use client";

import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";

export default function Home() {
  const { user, signIn } = useAuth();
  const router = useRouter();

  const handleSignIn = async () => {
    try {
      await signIn();
      router.push("/dashboard");
    } catch {
      // User cancelled sign-in
    }
  };

  return (
    <main className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4">
        <span className="text-2xl font-serif font-bold">Nonna</span>
        <div className="flex items-center gap-4">
          {user ? (
            <Link
              href="/dashboard"
              className="bg-nonna-accent text-white px-6 py-2 rounded-xl
                         hover:bg-nonna-brown transition-colors font-semibold"
            >
              My Families
            </Link>
          ) : (
            <button
              onClick={handleSignIn}
              className="bg-nonna-accent text-white px-6 py-2 rounded-xl
                         hover:bg-nonna-brown transition-colors font-semibold"
            >
              Sign In
            </button>
          )}
        </div>
      </nav>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-20 text-center">
        <h1 className="text-5xl md:text-7xl font-serif font-bold text-nonna-dark mb-6">
          Nonna
        </h1>
        <p className="text-xl md:text-2xl text-nonna-brown max-w-2xl mb-4">
          Every family has stories worth keeping forever.
        </p>
        <p className="text-lg text-nonna-brown/80 max-w-xl mb-12">
          Nonna is a warm AI companion who calls your parent or grandparent,
          listens to their stories, and transforms every conversation into a
          beautiful Memory Reel your family keeps forever.
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <Link
            href="/setup"
            className="inline-block bg-nonna-accent text-white text-xl font-semibold
                       px-10 py-5 rounded-2xl hover:bg-nonna-brown transition-colors
                       shadow-lg hover:shadow-xl min-h-[60px]"
          >
            Get Started
          </Link>
          {!user && (
            <button
              onClick={handleSignIn}
              className="inline-block border-2 border-nonna-accent text-nonna-accent
                         text-xl font-semibold px-10 py-5 rounded-2xl
                         hover:bg-nonna-accent/10 transition-colors min-h-[60px]"
            >
              Sign In
            </button>
          )}
        </div>
      </section>

      {/* How It Works */}
      <section className="bg-nonna-warm/50 px-6 py-20">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-serif font-bold text-center mb-16">
            How It Works
          </h2>
          <div className="grid md:grid-cols-3 gap-12">
            <div className="text-center">
              <div className="text-4xl mb-4">1</div>
              <h3 className="text-xl font-bold mb-3">You Set It Up</h3>
              <p className="text-nonna-brown/80">
                Enter your parent&apos;s name, phone number, and a few details
                about their life. Pick a call schedule.
              </p>
            </div>
            <div className="text-center">
              <div className="text-4xl mb-4">2</div>
              <h3 className="text-xl font-bold mb-3">Nonna Calls Them</h3>
              <p className="text-nonna-brown/80">
                Nonna calls at the scheduled time. They just pick up the phone
                and talk — about anything. She remembers everything.
              </p>
            </div>
            <div className="text-center">
              <div className="text-4xl mb-4">3</div>
              <h3 className="text-xl font-bold mb-3">Your Family Explores</h3>
              <p className="text-nonna-brown/80">
                Browse a rich archive of stories, search by topic, curate
                collections, and order a keepsake book.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-20">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-serif font-bold text-center mb-16">
            Why Families Love Nonna
          </h2>
          <div className="grid md:grid-cols-2 gap-8">
            {[
              {
                title: "She Remembers Everything",
                desc: "Nonna builds a relationship over weeks and months. She remembers names, stories, and follows up naturally.",
              },
              {
                title: "Zero Friction for Your Parent",
                desc: "They just pick up the phone. No apps, no passwords, no tech skills needed.",
              },
              {
                title: "Rich Family Archive",
                desc: "Browse stories by timeline, people, themes, or search for any topic. Your family's wisdom, organized beautifully.",
              },
              {
                title: "Keepsake Books",
                desc: "Turn conversations into a printed hardcover book with illustrations and quotes. A gift that lasts generations.",
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className="bg-white/60 rounded-2xl p-8 shadow-sm"
              >
                <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
                <p className="text-nonna-brown/80">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="text-center py-8 text-nonna-brown/60 text-sm">
        <p>Nonna — Preserving family stories, one conversation at a time.</p>
      </footer>
    </main>
  );
}
