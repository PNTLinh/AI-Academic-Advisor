"use client"

import { FileText, Bot, User } from "lucide-react"
import { StudyGoalsWidget } from "./study-goals-widget"

interface TranscriptRow {
  code: string
  name: string
  grade: string
  credits: number
}

interface ChatMessageProps {
  type: "user" | "assistant"
  content?: string
  attachment?: {
    name: string
    type: "pdf"
  }
  transcriptData?: TranscriptRow[]
  onConfirmData?: () => void
  isConfirmed?: boolean
  showStudyGoals?: boolean
  onStudyGoalsComplete?: (data: { effort: string; blackoutSlots: string[] }) => void
}

export function ChatMessage({
  type,
  content,
  attachment,
  transcriptData,
  onConfirmData,
  isConfirmed,
  showStudyGoals,
  onStudyGoalsComplete,
}: ChatMessageProps) {
  return (
    <div
      className={`flex gap-3 ${type === "user" ? "justify-end" : "justify-start"}`}
    >
      {type === "assistant" && (
        <div className="w-8 h-8 rounded-full bg-[var(--mint)] flex items-center justify-center flex-shrink-0">
          <Bot className="w-4 h-4 text-[#1a3a3a]" strokeWidth={1.5} />
        </div>
      )}

      <div
        className={`max-w-[85%] ${
          type === "user"
            ? "bg-[var(--mint)] text-[#1a3a3a] rounded-2xl rounded-br-md px-4 py-3"
            : "bg-card border border-border rounded-2xl rounded-bl-md px-4 py-3"
        }`}
      >
        {content && <p className="text-sm leading-relaxed">{content}</p>}

        {attachment && (
          <div className="flex items-center gap-2 bg-[var(--light-pink)] rounded-xl px-3 py-2 mt-2">
            <div className="w-8 h-8 rounded-lg bg-[var(--pink)] flex items-center justify-center">
              <FileText className="w-4 h-4 text-[#4a2c2f]" strokeWidth={1.5} />
            </div>
            <div>
              <p className="text-xs font-medium text-foreground">{attachment.name}</p>
              <p className="text-[10px] text-muted-foreground uppercase">PDF Document</p>
            </div>
          </div>
        )}

        {showStudyGoals && (
          <div className="mt-4">
            <StudyGoalsWidget onComplete={onStudyGoalsComplete} />
          </div>
        )}

        {transcriptData && (
          <div className="mt-3">
            <div className="overflow-hidden rounded-xl border border-border bg-background">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-[var(--muted)]">
                    <th className="px-3 py-2 text-left font-semibold text-foreground">Code</th>
                    <th className="px-3 py-2 text-left font-semibold text-foreground">Course Name</th>
                    <th className="px-3 py-2 text-center font-semibold text-foreground">Grade</th>
                    <th className="px-3 py-2 text-center font-semibold text-foreground">Credits</th>
                  </tr>
                </thead>
                <tbody>
                  {transcriptData.map((row, idx) => (
                    <tr
                      key={idx}
                      className={`border-t border-border ${
                        row.grade === "F" ? "bg-[var(--light-pink)]/30" : ""
                      }`}
                    >
                      <td className="px-3 py-2 font-mono text-muted-foreground">{row.code}</td>
                      <td className="px-3 py-2 text-foreground">{row.name}</td>
                      <td
                        className={`px-3 py-2 text-center font-semibold ${
                          row.grade === "F"
                            ? "text-[var(--pink)]"
                            : row.grade === "A" || row.grade === "A+"
                            ? "text-[var(--mint)]"
                            : "text-foreground"
                        }`}
                      >
                        {row.grade}
                      </td>
                      <td className="px-3 py-2 text-center text-muted-foreground">{row.credits}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button
              onClick={onConfirmData}
              disabled={isConfirmed}
              className={`mt-3 w-full py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 ${
                isConfirmed
                  ? "bg-[var(--cyan)] text-[#1a3a3a]"
                  : "bg-[var(--mint)] hover:bg-[#6bcbca] text-[#1a3a3a]"
              }`}
            >
              {isConfirmed ? "Data Confirmed" : "Confirm Data"}
            </button>
          </div>
        )}
      </div>

      {type === "user" && (
        <div className="w-8 h-8 rounded-full bg-[var(--light-pink)] flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4 text-[#4a2c2f]" strokeWidth={1.5} />
        </div>
      )}
    </div>
  )
}
