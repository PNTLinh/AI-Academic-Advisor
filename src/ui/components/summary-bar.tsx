"use client"

import { GraduationCap, Scale } from "lucide-react"

interface SummaryBarProps {
  totalCredits: number
  loadBalance: string
}

export function SummaryBar({ totalCredits, loadBalance }: SummaryBarProps) {
  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 sm:gap-8 p-5 bg-card rounded-2xl border border-border/50 shadow-sm">
      <div className="flex items-center gap-3 flex-1">
        <div className="w-10 h-10 rounded-xl bg-[var(--mint)]/20 flex items-center justify-center">
          <GraduationCap className="w-5 h-5 text-[var(--mint)]" strokeWidth={1.5} />
        </div>
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium">Total Credits</p>
          <p className="text-xl font-bold text-card-foreground">{totalCredits}</p>
        </div>
      </div>
      <div className="hidden sm:block w-px h-12 bg-border" />
      <div className="flex items-center gap-3 flex-1">
        <div className="w-10 h-10 rounded-xl bg-[var(--cyan)]/30 flex items-center justify-center">
          <Scale className="w-5 h-5 text-[#4a9e8a]" strokeWidth={1.5} />
        </div>
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium">Load Balance</p>
          <p className="text-xl font-bold text-card-foreground">{loadBalance}</p>
        </div>
      </div>
    </div>
  )
}
