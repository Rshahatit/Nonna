import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col">
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
        <Link
          href="/setup"
          className="inline-block bg-nonna-accent text-white text-xl font-semibold
                     px-10 py-5 rounded-2xl hover:bg-nonna-brown transition-colors
                     shadow-lg hover:shadow-xl min-h-[60px]"
        >
          Set Up Nonna for Your Family
        </Link>
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
              <h3 className="text-xl font-bold mb-3">You Get Memory Reels</h3>
              <p className="text-nonna-brown/80">
                After each conversation, Nonna creates a short narrated video
                with beautiful illustrations of your parent&apos;s stories.
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
                title: "Vision-Enabled Conversations",
                desc: "On a tablet, Nonna can see photos and objects — sparking deeper stories about what she sees.",
              },
              {
                title: "Beautiful Memory Reels",
                desc: "Every conversation becomes a short video with warm illustrations and narration your family keeps forever.",
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
