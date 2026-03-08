"use client";

export type SessionMode = "story" | "navigator" | "check_in" | "assist";

interface ModeSelectorProps {
  onSelectMode: (mode: SessionMode) => void;
  selectedMode: SessionMode;
}

const MODES: { mode: SessionMode; label: string; description: string; color: string; icon: string }[] = [
  {
    mode: "story",
    label: "Share Stories",
    description: "Tell Nonna about your life",
    color: "bg-nonna-accent hover:bg-nonna-brown",
    icon: "📖",
  },
  {
    mode: "navigator",
    label: "Help With My Screen",
    description: "Nonna guides you step by step",
    color: "bg-blue-500 hover:bg-blue-600",
    icon: "📱",
  },
  {
    mode: "assist",
    label: "Quick Help",
    description: "Ask Nonna anything",
    color: "bg-orange-400 hover:bg-orange-500",
    icon: "❓",
  },
];

export default function ModeSelector({ onSelectMode, selectedMode }: ModeSelectorProps) {
  return (
    <div className="space-y-4 w-full max-w-sm">
      {MODES.map(({ mode, label, description, color, icon }) => (
        <button
          key={mode}
          onClick={() => onSelectMode(mode)}
          className={`w-full flex items-center gap-4 p-5 rounded-2xl text-white
                     text-left transition-all active:scale-95 shadow-lg
                     ${color}
                     ${selectedMode === mode ? "ring-4 ring-white/50 scale-105" : ""}`}
        >
          <span className="text-4xl">{icon}</span>
          <div>
            <div className="text-xl font-bold">{label}</div>
            <div className="text-sm opacity-80">{description}</div>
          </div>
        </button>
      ))}
    </div>
  );
}
