"use client"

import { useState } from "react"
import { Feather, BookOpen, Rocket, Briefcase, Check } from "lucide-react"

const effortLevels = [
  {
    id: "light",
    title: "Light",
    credits: "12-15 credits",
    description: "More time for work, hobbies, or recovery",
    icon: Feather,
    recommended: false,
  },
  {
    id: "standard",
    title: "Standard",
    credits: "15-18 credits",
    description: "Balanced workload, on-track graduation",
    icon: BookOpen,
    recommended: true,
  },
  {
    id: "accelerated",
    title: "Accelerated",
    credits: "18-22 credits",
    description: "Fast-track progress, intensive study",
    icon: Rocket,
    recommended: false,
  },
]

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
const timeSlots = [
  { label: "Morning", time: "8AM-12PM" },
  { label: "Afternoon", time: "12PM-5PM" },
  { label: "Evening", time: "5PM-9PM" },
]

interface StudyGoalsWidgetProps {
  onComplete?: (data: { effort: string; blackoutSlots: string[] }) => void
}

export function StudyGoalsWidget({ onComplete }: StudyGoalsWidgetProps) {
  const [selectedEffort, setSelectedEffort] = useState<string | null>(null)
  const [blackoutSlots, setBlackoutSlots] = useState<Set<string>>(new Set())
  const [isSubmitted, setIsSubmitted] = useState(false)

  const toggleBlackoutSlot = (day: string, slot: string) => {
    const key = `${day}-${slot}`
    const newSlots = new Set(blackoutSlots)
    if (newSlots.has(key)) {
      newSlots.delete(key)
    } else {
      newSlots.add(key)
    }
    setBlackoutSlots(newSlots)
  }

  const handleSubmit = () => {
    if (selectedEffort) {
      setIsSubmitted(true)
      onComplete?.({
        effort: selectedEffort,
        blackoutSlots: Array.from(blackoutSlots),
      })
    }
  }

  return (
    <div className="space-y-5">
      {/* Effort Cards */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Study Load Preference
        </p>
        <div className="grid gap-2">
          {effortLevels.map((level) => {
            const Icon = level.icon
            const isSelected = selectedEffort === level.id
            return (
              <button
                key={level.id}
                onClick={() => !isSubmitted && setSelectedEffort(level.id)}
                disabled={isSubmitted}
                className={`relative flex items-center gap-3 p-3 rounded-xl border-2 transition-all duration-200 text-left ${
                  isSelected
                    ? "border-[var(--mint)] bg-[var(--mint)]/10"
                    : "border-border bg-background hover:border-[var(--cyan)] hover:bg-[var(--cyan)]/5"
                } ${isSubmitted ? "cursor-default" : "cursor-pointer"}`}
              >
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    isSelected ? "bg-[var(--mint)]" : "bg-[var(--muted)]"
                  }`}
                >
                  <Icon
                    className={`w-5 h-5 ${isSelected ? "text-[#1a3a3a]" : "text-muted-foreground"}`}
                    strokeWidth={1.5}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-foreground">{level.title}</span>
                    <span className="text-xs text-muted-foreground">({level.credits})</span>
                    {level.recommended && (
                      <span className="px-1.5 py-0.5 text-[10px] font-medium bg-[var(--cyan)] text-[#1a3a3a] rounded-md">
                        Recommended
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">{level.description}</p>
                </div>
                {isSelected && (
                  <div className="w-5 h-5 rounded-full bg-[var(--mint)] flex items-center justify-center flex-shrink-0">
                    <Check className="w-3 h-3 text-[#1a3a3a]" strokeWidth={2.5} />
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Blackout Period Calendar */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Briefcase className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} />
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Block Unavailable Times
          </p>
        </div>
        <p className="text-xs text-muted-foreground">
          Click to mark times when you have work, internships, or other commitments
        </p>
        <div className="bg-background rounded-xl border border-border overflow-hidden">
          {/* Calendar Header */}
          <div className="grid grid-cols-8 border-b border-border bg-[var(--muted)]">
            <div className="p-2" />
            {days.map((day) => (
              <div
                key={day}
                className="p-2 text-center text-[10px] font-semibold text-foreground"
              >
                {day}
              </div>
            ))}
          </div>
          {/* Calendar Body */}
          {timeSlots.map((slot) => (
            <div key={slot.label} className="grid grid-cols-8 border-b border-border last:border-b-0">
              <div className="p-2 flex flex-col justify-center border-r border-border bg-[var(--muted)]">
                <span className="text-[10px] font-medium text-foreground">{slot.label}</span>
                <span className="text-[8px] text-muted-foreground">{slot.time}</span>
              </div>
              {days.map((day) => {
                const key = `${day}-${slot.label}`
                const isBlocked = blackoutSlots.has(key)
                return (
                  <button
                    key={key}
                    onClick={() => !isSubmitted && toggleBlackoutSlot(day, slot.label)}
                    disabled={isSubmitted}
                    className={`p-2 min-h-[40px] transition-all duration-150 ${
                      isBlocked
                        ? "bg-[var(--pink)] hover:bg-[var(--light-pink)]"
                        : "bg-background hover:bg-[var(--cyan)]/20"
                    } ${isSubmitted ? "cursor-default" : "cursor-pointer"}`}
                  >
                    {isBlocked && (
                      <div className="w-full h-full flex items-center justify-center">
                        <Briefcase className="w-3 h-3 text-[#4a2c2f]" strokeWidth={2} />
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          ))}
        </div>
        <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded bg-[var(--pink)]" />
            <span>Blocked</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded bg-background border border-border" />
            <span>Available</span>
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={!selectedEffort || isSubmitted}
        className={`w-full py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 ${
          isSubmitted
            ? "bg-[var(--cyan)] text-[#1a3a3a]"
            : selectedEffort
            ? "bg-[var(--mint)] hover:bg-[#6bcbca] text-[#1a3a3a]"
            : "bg-border text-muted-foreground cursor-not-allowed"
        }`}
      >
        {isSubmitted
          ? "Preferences Saved"
          : `Set My Study Goals${blackoutSlots.size > 0 ? ` (${blackoutSlots.size} blocked)` : ""}`}
      </button>
    </div>
  )
}
