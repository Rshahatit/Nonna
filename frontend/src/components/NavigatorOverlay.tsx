"use client";

interface NavigatorOverlayProps {
  isCapturing: boolean;
  onCaptureScreenshot: () => void;
  encouragement: string | null;
}

export default function NavigatorOverlay({
  isCapturing,
  onCaptureScreenshot,
  encouragement,
}: NavigatorOverlayProps) {
  return (
    <div className="w-full max-w-lg space-y-4">
      {/* Screen capture indicator */}
      <div className="flex items-center justify-center gap-2 text-nonna-brown/70">
        <div
          className={`w-3 h-3 rounded-full ${
            isCapturing ? "bg-green-500 animate-pulse" : "bg-gray-400"
          }`}
        />
        <span className="text-lg">
          {isCapturing
            ? "Nonna can see your screen"
            : "Tap below to share your screen with Nonna"}
        </span>
      </div>

      {/* Encouragement message */}
      {encouragement && (
        <div className="bg-nonna-sage/30 rounded-xl p-4 text-center">
          <p className="text-elder text-nonna-brown font-medium">{encouragement}</p>
        </div>
      )}

      {/* Capture button */}
      <button
        onClick={onCaptureScreenshot}
        className="w-full py-5 rounded-2xl bg-blue-500 text-white text-xl
                   font-bold shadow-lg hover:bg-blue-600 transition-all
                   active:scale-95"
      >
        {isCapturing ? "Share Screen Again" : "Share My Screen"}
      </button>
    </div>
  );
}
