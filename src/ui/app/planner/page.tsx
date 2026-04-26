"use client"

import { useState } from "react"
import {
  Bot,
  Calendar,
  Sparkles,
  Scale,
  Zap,
  ArrowRight,
  CheckCircle2,
  Map,
} from "lucide-react"
import { SmartRoadmap } from "@/components/smart-roadmap"
import Link from "next/link"

type Scenario = "balanced" | "accelerated"

export default function PlannerPage() {
  const [scenario, setScenario] = useState<Scenario>("balanced")
  const [syncStatus, setSyncStatus] = useState<"idle" | "syncing" | "synced">("idle")

  const handleSync = () => {
    setSyncStatus("syncing")
    setTimeout(() => {
      setSyncStatus("synced")
      setTimeout(() => setSyncStatus("idle"), 2000)
    }, 1500)
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="h-screen flex flex-col">
        {/* Top Navigation Bar */}
        <header className="px-4 sm:px-6 py-3 border-b border-border bg-card flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/advisor"
              className="w-9 h-9 rounded-xl bg-[var(--mint)] flex items-center justify-center hover:bg-[#6bcbca] transition-colors"
            >
              <Bot className="w-4 h-4 text-[#1a3a3a]" strokeWidth={1.5} />
            </Link>
            <div>
              <h1 className="font-semibold text-foreground text-sm sm:text-base">AI Study Planner</h1>
              <p className="text-xs text-muted-foreground hidden sm:block">Personalized Academic Roadmap</p>
            </div>
          </div>

          {/* Scenario Toggle */}
          <div className="flex items-center gap-2 p-1 bg-[var(--muted)] rounded-xl">
            <button
              onClick={() => setScenario("balanced")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                scenario === "balanced"
                  ? "bg-card shadow-sm text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Scale className="w-3.5 h-3.5" strokeWidth={1.5} />
              <span className="hidden sm:inline">Balanced Load</span>
              <span className="sm:hidden">Balanced</span>
            </button>
            <button
              onClick={() => setScenario("accelerated")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                scenario === "accelerated"
                  ? "bg-card shadow-sm text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Zap className="w-3.5 h-3.5" strokeWidth={1.5} />
              <span className="hidden sm:inline">Graduate Early</span>
              <span className="sm:hidden">Early</span>
            </button>
          </div>
        </header>

        {/* Main Content */}
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
          {/* Left: Chat History */}
          <div className="lg:w-[380px] xl:w-[420px] flex-shrink-0 border-b lg:border-b-0 lg:border-r border-border bg-card/50 flex flex-col max-h-[300px] lg:max-h-none">
            <div className="px-4 py-3 border-b border-border">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[var(--mint)]" strokeWidth={1.5} />
                <h2 className="text-sm font-medium text-foreground">AI Recommendation</h2>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              <div className="space-y-4">
                {/* AI Summary Message */}
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[var(--mint)] flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-[#1a3a3a]" strokeWidth={1.5} />
                  </div>
                  <div className="flex-1 bg-[var(--muted)] rounded-2xl rounded-tl-md p-4">
                    <p className="text-sm text-foreground leading-relaxed">
                      Based on your transcript analysis and study preferences, I&apos;ve created a personalized academic roadmap for you.
                    </p>
                  </div>
                </div>

                {/* Recommendation Card */}
                <div className="ml-11">
                  <div className="bg-card border border-border rounded-xl p-4 space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-lg bg-[var(--light-pink)] flex items-center justify-center flex-shrink-0">
                        <Map className="w-4 h-4 text-[#4a2c2f]" strokeWidth={1.5} />
                      </div>
                      <div>
                        <h3 className="font-medium text-foreground text-sm">
                          {scenario === "balanced" ? "Balanced Load Plan" : "Accelerated Graduation"}
                        </h3>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {scenario === "balanced"
                            ? "Graduate on schedule with manageable workload"
                            : "Finish 1 semester early with intensive schedule"}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div className="bg-[var(--muted)] rounded-lg p-2.5">
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Priority Focus</p>
                        <p className="text-sm font-medium text-foreground mt-0.5">Physics Retakes</p>
                      </div>
                      <div className="bg-[var(--muted)] rounded-lg p-2.5">
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Avg Credits/Sem</p>
                        <p className="text-sm font-medium text-foreground mt-0.5">
                          {scenario === "balanced" ? "13-16" : "16-20"}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Key Insights */}
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[var(--mint)] flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-[#1a3a3a]" strokeWidth={1.5} />
                  </div>
                  <div className="flex-1 bg-[var(--muted)] rounded-2xl rounded-tl-md p-4">
                    <p className="text-sm font-medium text-foreground mb-2">Key Insights:</p>
                    <ul className="space-y-1.5">
                      <li className="flex items-start gap-2 text-xs text-muted-foreground">
                        <CheckCircle2 className="w-3.5 h-3.5 text-[var(--mint)] flex-shrink-0 mt-0.5" strokeWidth={1.5} />
                        <span>Retaking Physics I & II early clears prerequisites</span>
                      </li>
                      <li className="flex items-start gap-2 text-xs text-muted-foreground">
                        <CheckCircle2 className="w-3.5 h-3.5 text-[var(--mint)] flex-shrink-0 mt-0.5" strokeWidth={1.5} />
                        <span>Summer sessions keep you on track without overload</span>
                      </li>
                      <li className="flex items-start gap-2 text-xs text-muted-foreground">
                        <CheckCircle2 className="w-3.5 h-3.5 text-[var(--mint)] flex-shrink-0 mt-0.5" strokeWidth={1.5} />
                        <span>Capstone project planned for final semester</span>
                      </li>
                    </ul>
                  </div>
                </div>

                {/* Action Prompt */}
                <div className="ml-11">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <ArrowRight className="w-3.5 h-3.5 text-[var(--mint)]" strokeWidth={1.5} />
                    <span>Toggle scenarios above to compare plans</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Smart Roadmap */}
          <div className="flex-1 flex flex-col overflow-hidden bg-background">
            <div className="px-4 sm:px-6 py-3 border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Map className="w-4 h-4 text-[var(--pink)]" strokeWidth={1.5} />
                <h2 className="text-sm font-medium text-foreground">Smart Roadmap</h2>
                <span className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-[var(--muted)] text-muted-foreground">
                  {scenario === "balanced" ? "4 Semesters" : "4 Semesters (Accelerated)"}
                </span>
              </div>
            </div>

            <div className="flex-1 overflow-hidden p-4 sm:p-6">
              <SmartRoadmap scenario={scenario} />
            </div>
          </div>
        </div>

        {/* Floating Sync Button */}
        <button
          onClick={handleSync}
          disabled={syncStatus === "syncing"}
          className={`fixed bottom-6 right-6 flex items-center gap-2 px-5 py-3 rounded-full shadow-lg transition-all hover:shadow-xl ${
            syncStatus === "synced"
              ? "bg-[var(--cyan)] text-[#1a3a3a]"
              : syncStatus === "syncing"
              ? "bg-[var(--muted)] text-muted-foreground cursor-wait"
              : "bg-[var(--mint)] text-[#1a3a3a] hover:bg-[#6bcbca]"
          }`}
        >
          <Calendar
            className={`w-4 h-4 ${syncStatus === "syncing" ? "animate-pulse" : ""}`}
            strokeWidth={1.5}
          />
          <span className="text-sm font-medium">
            {syncStatus === "syncing"
              ? "Syncing..."
              : syncStatus === "synced"
              ? "Synced!"
              : "Sync to Calendar"}
          </span>
          {syncStatus === "synced" && <CheckCircle2 className="w-4 h-4" strokeWidth={1.5} />}
        </button>
      </div>
    </main>
  )
}
