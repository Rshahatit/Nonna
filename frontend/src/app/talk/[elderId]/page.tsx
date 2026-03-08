"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useConversation } from "@/hooks/useConversation";
import type { SessionMode } from "@/hooks/useConversation";
import ModeSelector from "@/components/ModeSelector";
import NavigatorOverlay from "@/components/NavigatorOverlay";

export default function TalkPage() {
  const params = useParams();
  const elderId = params.elderId as string;
  const [selectedMode, setSelectedMode] = useState<SessionMode>("story");
  const {
    state,
    isSpeaking,
    mode,
    encouragement,
    start,
    stop,
    videoRef,
    captureScreenFromVideo,
  } = useConversation(elderId);

  const isNavigatorMode = mode === "navigator" || mode === "assist";

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6 py-12">
      {/* Idle state — mode selection + start */}
      {state === "idle" && (
        <div className="text-center space-y-8">
          <h1 className="text-elder-lg font-serif font-bold">
            Talk to Nonna
          </h1>
          <p className="text-elder text-nonna-brown/70">
            What would you like to do today?
          </p>

          <ModeSelector
            selectedMode={selectedMode}
            onSelectMode={setSelectedMode}
          />

          <button
            onClick={() => start(true, selectedMode)}
            className="w-56 h-56 rounded-full bg-nonna-accent text-white
                       text-3xl font-bold shadow-2xl hover:bg-nonna-brown
                       transition-all hover:scale-105 active:scale-95"
          >
            Start
          </button>
          <button
            onClick={() => start(false, selectedMode)}
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
          {/* Camera preview */}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`rounded-xl object-cover mx-auto ${
              isNavigatorMode
                ? "w-48 h-36 opacity-80"
                : "w-32 h-24 opacity-60"
            }`}
          />

          {/* Navigator/Assist overlay */}
          {isNavigatorMode && (
            <NavigatorOverlay
              isCapturing={true}
              onCaptureScreenshot={captureScreenFromVideo}
              encouragement={encouragement}
            />
          )}

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

          {/* Mode indicator */}
          <p className="text-sm text-nonna-brown/40">
            {mode === "story" && "Story Mode"}
            {mode === "navigator" && "Screen Guide Mode"}
            {mode === "check_in" && "Check-In Mode"}
            {mode === "assist" && "Help Mode"}
          </p>

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
            {mode === "story"
              ? "Thank you for sharing today."
              : "Great job today!"}
          </h2>
          <p className="text-elder text-nonna-brown/70">
            {mode === "story"
              ? "Your Memory Reel will be ready soon."
              : "Nonna is always here when you need help."}
          </p>
          {mode === "story" && (
            <p className="text-lg text-nonna-brown/50">
              Nonna is turning your stories into something beautiful.
            </p>
          )}
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
