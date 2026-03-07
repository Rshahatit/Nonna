"use client";

import { useState, useRef, useCallback, useEffect } from "react";

const WS_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000")
  .replace("https://", "wss://")
  .replace("http://", "ws://");

type ConversationState = "idle" | "connecting" | "active" | "ended";

export function useConversation(elderId: string) {
  const [state, setState] = useState<ConversationState>("idle");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const frameIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const start = useCallback(
    async (enableCamera: boolean = false) => {
      setState("connecting");

      try {
        // Get microphone (and optionally camera)
        const constraints: MediaStreamConstraints = {
          audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true },
        };
        if (enableCamera) {
          constraints.video = { facingMode: "environment", width: 640, height: 480 };
        }

        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        mediaStreamRef.current = stream;

        // Set up audio context for capturing
        const audioContext = new AudioContext({ sampleRate: 16000 });
        audioContextRef.current = audioContext;

        const source = audioContext.createMediaStreamSource(stream);
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        // Connect WebSocket
        const ws = new WebSocket(`${WS_URL}/ws/pwa-stream`);
        wsRef.current = ws;

        ws.onopen = () => {
          ws.send(JSON.stringify({ type: "start", elder_id: elderId }));
        };

        ws.onmessage = (event) => {
          const message = JSON.parse(event.data);

          if (message.type === "started") {
            setSessionId(message.session_id);
            setState("active");

            // Start sending audio
            processor.onaudioprocess = (e) => {
              if (ws.readyState !== WebSocket.OPEN) return;
              const inputData = e.inputBuffer.getChannelData(0);
              const pcm16 = new Int16Array(inputData.length);
              for (let i = 0; i < inputData.length; i++) {
                pcm16[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
              }
              const base64 = btoa(
                String.fromCharCode(...new Uint8Array(pcm16.buffer))
              );
              ws.send(JSON.stringify({ type: "audio", data: base64 }));
            };
            source.connect(processor);
            processor.connect(audioContext.destination);

            // Start sending camera frames if enabled
            if (enableCamera && videoRef.current) {
              const video = videoRef.current;
              video.srcObject = stream;
              video.play();

              frameIntervalRef.current = setInterval(() => {
                if (ws.readyState !== WebSocket.OPEN) return;
                const canvas = document.createElement("canvas");
                canvas.width = 640;
                canvas.height = 480;
                const ctx = canvas.getContext("2d");
                if (ctx) {
                  ctx.drawImage(video, 0, 0, 640, 480);
                  const dataUrl = canvas.toDataURL("image/jpeg", 0.5);
                  const base64 = dataUrl.split(",")[1];
                  ws.send(JSON.stringify({ type: "frame", data: base64 }));
                }
              }, 10000); // Every 10 seconds
            }
          } else if (message.type === "audio") {
            // Play Nonna's audio response
            setIsSpeaking(true);
            const audioData = atob(message.data);
            const arrayBuffer = new ArrayBuffer(audioData.length);
            const view = new Uint8Array(arrayBuffer);
            for (let i = 0; i < audioData.length; i++) {
              view[i] = audioData.charCodeAt(i);
            }
            audioContext.decodeAudioData(arrayBuffer).then((buffer) => {
              const source = audioContext.createBufferSource();
              source.buffer = buffer;
              source.connect(audioContext.destination);
              source.onended = () => setIsSpeaking(false);
              source.start();
            }).catch(() => setIsSpeaking(false));
          } else if (message.type === "error") {
            console.error("Server error:", message.message);
          }
        };

        ws.onerror = () => {
          setState("idle");
        };

        ws.onclose = () => {
          if (state === "active") {
            setState("ended");
          }
        };
      } catch (err) {
        console.error("Failed to start conversation:", err);
        setState("idle");
      }
    },
    [elderId, state]
  );

  const stop = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "stop" }));
      wsRef.current.close();
    }
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
    }
    if (processorRef.current) {
      processorRef.current.disconnect();
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }
    setState("ended");
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (mediaStreamRef.current) mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      if (audioContextRef.current) audioContextRef.current.close();
      if (frameIntervalRef.current) clearInterval(frameIntervalRef.current);
    };
  }, []);

  return { state, sessionId, isSpeaking, start, stop, videoRef };
}
