"use client";

import { useState } from "react";
import { api, type CallSchedule } from "@/lib/api";
import Link from "next/link";

const DAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
];

export default function SetupPage() {
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [seedContext, setSeedContext] = useState("");
  const [selectedDays, setSelectedDays] = useState<string[]>([]);
  const [callTime, setCallTime] = useState("14:00");
  const [timezone, setTimezone] = useState("America/New_York");
  const [createdBy, setCreatedBy] = useState("");

  const [elderId, setElderId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleDay = (day: string) => {
    setSelectedDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    );
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const schedule: CallSchedule = {
        days: selectedDays,
        time: callTime,
        timezone,
      };
      const elder = await api.createElder({
        name,
        phone_number: phone,
        seed_context: seedContext,
        call_schedule: schedule,
        created_by: createdBy,
      });
      setElderId(elder.id);
      setStep(5);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const triggerFirstCall = async () => {
    if (!elderId) return;
    try {
      await api.triggerCall(elderId);
      alert("Nonna is calling now!");
    } catch {
      alert("Could not place the call right now. Nonna will call at the scheduled time.");
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center px-6 py-12">
      <Link href="/" className="text-nonna-accent mb-8 hover:underline">
        &larr; Back to Home
      </Link>

      <h1 className="text-4xl font-serif font-bold mb-2">Set Up Nonna</h1>
      <p className="text-nonna-brown/70 mb-12 text-center max-w-md">
        Tell us about your parent or grandparent so Nonna can get to know them.
      </p>

      {/* Progress */}
      <div className="flex items-center gap-2 mb-12">
        {[1, 2, 3, 4].map((s) => (
          <div
            key={s}
            className={`w-3 h-3 rounded-full transition-colors ${
              s <= step ? "bg-nonna-accent" : "bg-nonna-warm"
            }`}
          />
        ))}
      </div>

      <div className="w-full max-w-lg">
        {/* Step 1: Name + Your Contact */}
        {step === 1 && (
          <div className="space-y-6">
            <div>
              <label className="block text-lg font-semibold mb-2">
                What is their name?
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Maria, Grandpa Joe"
                className="w-full text-xl p-4 rounded-xl border-2 border-nonna-warm
                           focus:border-nonna-accent bg-white"
              />
            </div>
            <div>
              <label className="block text-lg font-semibold mb-2">
                Your phone number or email
              </label>
              <input
                type="text"
                value={createdBy}
                onChange={(e) => setCreatedBy(e.target.value)}
                placeholder="+1234567890 or you@email.com"
                className="w-full text-xl p-4 rounded-xl border-2 border-nonna-warm
                           focus:border-nonna-accent bg-white"
              />
              <p className="text-sm text-nonna-brown/50 mt-1">
                We&apos;ll notify you when new Memory Reels are ready.
              </p>
            </div>
            <button
              onClick={() => setStep(2)}
              disabled={!name.trim()}
              className="w-full bg-nonna-accent text-white text-xl font-semibold
                         py-4 rounded-xl hover:bg-nonna-brown transition-colors
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}

        {/* Step 2: Phone Number */}
        {step === 2 && (
          <div className="space-y-6">
            <div>
              <label className="block text-lg font-semibold mb-2">
                What is {name}&apos;s phone number?
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+1 (555) 123-4567"
                className="w-full text-xl p-4 rounded-xl border-2 border-nonna-warm
                           focus:border-nonna-accent bg-white"
              />
              <p className="text-sm text-nonna-brown/50 mt-1">
                Nonna will call this number. Any phone works — landline or cell.
              </p>
            </div>
            <div className="flex gap-4">
              <button
                onClick={() => setStep(1)}
                className="flex-1 border-2 border-nonna-warm text-nonna-brown text-lg
                           py-4 rounded-xl hover:bg-nonna-warm/50 transition-colors"
              >
                Back
              </button>
              <button
                onClick={() => setStep(3)}
                disabled={!phone.trim()}
                className="flex-1 bg-nonna-accent text-white text-lg font-semibold
                           py-4 rounded-xl hover:bg-nonna-brown transition-colors
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Seed Context */}
        {step === 3 && (
          <div className="space-y-6">
            <div>
              <label className="block text-lg font-semibold mb-2">
                Tell Nonna a bit about {name}
              </label>
              <textarea
                value={seedContext}
                onChange={(e) => setSeedContext(e.target.value)}
                rows={6}
                placeholder={`Help Nonna get started. For example:\n\n"Mom grew up in Amman, Jordan. She's an amazing cook — her stuffed grape leaves are legendary. Dad passed away 2 years ago. She has 3 kids and 5 grandchildren. She loves gardening and old Egyptian movies."`}
                className="w-full text-lg p-4 rounded-xl border-2 border-nonna-warm
                           focus:border-nonna-accent bg-white resize-none"
              />
              <p className="text-sm text-nonna-brown/50 mt-1">
                The more you share, the better Nonna&apos;s first conversation will be.
              </p>
            </div>
            <div className="flex gap-4">
              <button
                onClick={() => setStep(2)}
                className="flex-1 border-2 border-nonna-warm text-nonna-brown text-lg
                           py-4 rounded-xl hover:bg-nonna-warm/50 transition-colors"
              >
                Back
              </button>
              <button
                onClick={() => setStep(4)}
                className="flex-1 bg-nonna-accent text-white text-lg font-semibold
                           py-4 rounded-xl hover:bg-nonna-brown transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Schedule */}
        {step === 4 && (
          <div className="space-y-6">
            <div>
              <label className="block text-lg font-semibold mb-4">
                When should Nonna call {name}?
              </label>
              <div className="flex flex-wrap gap-3 mb-6">
                {DAYS.map((day) => (
                  <button
                    key={day}
                    onClick={() => toggleDay(day)}
                    className={`px-5 py-3 rounded-xl text-lg capitalize transition-colors ${
                      selectedDays.includes(day)
                        ? "bg-nonna-accent text-white"
                        : "bg-white border-2 border-nonna-warm text-nonna-brown"
                    }`}
                  >
                    {day.slice(0, 3)}
                  </button>
                ))}
              </div>
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-semibold mb-1">
                    Preferred time
                  </label>
                  <input
                    type="time"
                    value={callTime}
                    onChange={(e) => setCallTime(e.target.value)}
                    className="w-full text-xl p-4 rounded-xl border-2 border-nonna-warm
                               focus:border-nonna-accent bg-white"
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-sm font-semibold mb-1">
                    Timezone
                  </label>
                  <select
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    className="w-full text-lg p-4 rounded-xl border-2 border-nonna-warm
                               focus:border-nonna-accent bg-white"
                  >
                    <option value="America/New_York">Eastern</option>
                    <option value="America/Chicago">Central</option>
                    <option value="America/Denver">Mountain</option>
                    <option value="America/Los_Angeles">Pacific</option>
                  </select>
                </div>
              </div>
            </div>
            {error && (
              <p className="text-red-600 bg-red-50 p-4 rounded-xl">{error}</p>
            )}
            <div className="flex gap-4">
              <button
                onClick={() => setStep(3)}
                className="flex-1 border-2 border-nonna-warm text-nonna-brown text-lg
                           py-4 rounded-xl hover:bg-nonna-warm/50 transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading || selectedDays.length === 0}
                className="flex-1 bg-nonna-accent text-white text-lg font-semibold
                           py-4 rounded-xl hover:bg-nonna-brown transition-colors
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Setting up..." : "Create Nonna"}
              </button>
            </div>
          </div>
        )}

        {/* Step 5: Confirmation */}
        {step === 5 && elderId && (
          <div className="text-center space-y-8">
            <div className="text-6xl">&#10024;</div>
            <h2 className="text-3xl font-serif font-bold">
              Nonna is Ready for {name}!
            </h2>
            <p className="text-lg text-nonna-brown/80">
              Nonna will call {name} at the scheduled times. They just need to
              pick up the phone and talk.
            </p>

            <div className="bg-white rounded-2xl p-6 shadow-sm space-y-4">
              <h3 className="font-semibold text-lg">Your Family Archive</h3>
              <p className="text-nonna-brown/70">
                Bookmark this link to watch Memory Reels as they&apos;re
                created:
              </p>
              <Link
                href={`/archive/${elderId}`}
                className="text-nonna-accent hover:underline text-lg break-all"
              >
                {typeof window !== "undefined"
                  ? window.location.origin
                  : ""}/archive/{elderId}
              </Link>
            </div>

            <div className="space-y-4">
              <button
                onClick={triggerFirstCall}
                className="w-full bg-nonna-accent text-white text-xl font-semibold
                           py-4 rounded-xl hover:bg-nonna-brown transition-colors"
              >
                Call {name} Now
              </button>
              <Link
                href={`/talk/${elderId}`}
                className="block w-full border-2 border-nonna-accent text-nonna-accent
                           text-xl font-semibold py-4 rounded-xl hover:bg-nonna-accent/10
                           transition-colors text-center"
              >
                Open Video Chat Instead
              </Link>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
