"use client";

import { useParams } from "next/navigation";
import { useConversation } from "@/hooks/useConversation";

export default function TalkPage() {
  const params = useParams();
  const elderId = params.elderId as string;
  const { state, isSpeaking, start, stop, videoRef } =
    useConversation(elderId);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6 py-12">
      {/* Idle state — big button */}
      {state === "idle" && (
        <div className="text-center space-y-8">
          <h1 className="text-elder-lg font-serif font-bold">
            Talk to Nonna
          </h1>
          <p className="text-elder text-nonna-brown/70">
            Tap the button below to start a conversation.
          </p>
          <button
            onClick={() => start(true)}
            className="w-64 h-64 rounded-full bg-nonna-accent text-white
                       text-3xl font-bold shadow-2xl hover:bg-nonna-brown
                       transition-all hover:scale-105 active:scale-95"
          >
            Talk to<br />Nonna
          </button>
          <button
            onClick={() => start(false)}
            className="block mx-auto text-nonna-brown/60 hover:text-nonna-brown
                       underline text-lg"
          >
            Start without camera
          </button>
        </div>
      )}

      {/* Connecting */}
      {state === "connecting" && (
        <div className="text-center space-y-6">
          <div className="w-24 h-24 rounded-full border-4 border-nonna-accent border-t-transparent animate-spin mx-auto" />
          <p className="text-elder text-nonna-brown/70">
            Connecting to Nonna...
          </p>
        </div>
      )}

      {/* Active conversation */}
      {state === "active" && (
        <div className="text-center space-y-8 w-full max-w-lg">
          {/* Camera preview (small) */}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-32 h-24 rounded-xl object-cover mx-auto opacity-60"
          />

          {/* Speaking indicator */}
          <div className="flex items-center justify-center gap-3">
            <div
              className={`w-4 h-4 rounded-full transition-colors ${
                isSpeaking ? "bg-nonna-accent animate-pulse" : "bg-nonna-sage"
              }`}
            />
            <p className="text-elder text-nonna-brown/70">
              {isSpeaking ? "Nonna is speaking..." : "Nonna is listening..."}
            </p>
          </div>

          {/* End button */}
          <button
            onClick={stop}
            className="w-48 h-48 rounded-full bg-nonna-rose text-nonna-dark
                       text-2xl font-bold shadow-xl hover:bg-red-300
                       transition-all active:scale-95"
          >
            End<br />Conversation
          </button>
        </div>
      )}

      {/* Ended */}
      {state === "ended" && (
        <div className="text-center space-y-8">
          <h2 className="text-elder-lg font-serif font-bold">
            Thank you for sharing today.
          </h2>
          <p className="text-elder text-nonna-brown/70">
            Your Memory Reel will be ready soon.
          </p>
          <p className="text-lg text-nonna-brown/50">
            Nonna is turning your stories into something beautiful.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="bg-nonna-accent text-white text-xl font-semibold
                       px-10 py-4 rounded-xl hover:bg-nonna-brown transition-colors"
          >
            Talk Again
          </button>
        </div>
      )}
    </main>
  );
}
