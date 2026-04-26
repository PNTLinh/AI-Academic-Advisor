"use client"

import { GraduationCap, BookOpen, AlertTriangle, TrendingUp, Award } from "lucide-react"

interface StudentProfile {
  gpa: number
  creditsEarned: number
  totalCredits: number
  failedCourses: {
    code: string
    name: string
    semester: string
  }[]
  standing: "Good" | "Warning" | "Probation"
}

interface StudentProfilePanelProps {
  profile: StudentProfile
  isDataConfirmed: boolean
}

export function StudentProfilePanel({ profile, isDataConfirmed }: StudentProfilePanelProps) {
  const progressPercent = (profile.creditsEarned / profile.totalCredits) * 100

  return (
    <div className="h-full flex flex-col bg-card rounded-2xl border border-border overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-border bg-[var(--muted)]">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[var(--mint)] flex items-center justify-center">
            <GraduationCap className="w-4 h-4 text-[#1a3a3a]" strokeWidth={1.5} />
          </div>
          <div>
            <h2 className="font-semibold text-foreground">Student Persona</h2>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide">
              Extracted from Transcript
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-5 space-y-5 overflow-y-auto">
        {!isDataConfirmed ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-muted-foreground">
              <div className="w-12 h-12 rounded-full bg-[var(--muted)] flex items-center justify-center mx-auto mb-3">
                <BookOpen className="w-5 h-5" strokeWidth={1.5} />
              </div>
              <p className="text-sm">Waiting for data confirmation...</p>
              <p className="text-xs mt-1">Upload and confirm your transcript</p>
            </div>
          </div>
        ) : (
          <>
            {/* GPA Card */}
            <div className="bg-[var(--muted)] rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Award className="w-4 h-4 text-[var(--mint)]" strokeWidth={1.5} />
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Cumulative GPA
                  </span>
                </div>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                    profile.standing === "Good"
                      ? "bg-[var(--cyan)] text-[#1a3a3a]"
                      : profile.standing === "Warning"
                      ? "bg-[var(--light-pink)] text-[#4a2c2f]"
                      : "bg-[var(--pink)] text-[#4a2c2f]"
                  }`}
                >
                  {profile.standing} Standing
                </span>
              </div>
              <p className="text-3xl font-bold text-foreground">{profile.gpa.toFixed(2)}</p>
              <p className="text-xs text-muted-foreground mt-1">out of 4.00</p>
            </div>

            {/* Credits Progress */}
            <div className="bg-[var(--muted)] rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-[var(--mint)]" strokeWidth={1.5} />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Credits Progress
                </span>
              </div>
              <div className="flex items-end justify-between mb-2">
                <p className="text-2xl font-bold text-foreground">{profile.creditsEarned}</p>
                <p className="text-sm text-muted-foreground">/ {profile.totalCredits} credits</p>
              </div>
              <div className="h-2 bg-border rounded-full overflow-hidden">
                <div
                  className="h-full bg-[var(--mint)] rounded-full transition-all duration-500"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {Math.round(progressPercent)}% toward graduation
              </p>
            </div>

            {/* Failed Courses */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-[var(--pink)]" strokeWidth={1.5} />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Failed Courses ({profile.failedCourses.length})
                </span>
              </div>
              <div className="space-y-2">
                {profile.failedCourses.map((course, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between bg-[var(--light-pink)]/40 rounded-xl px-3 py-2.5 border border-[var(--pink)]/20"
                  >
                    <div>
                      <p className="text-sm font-medium text-foreground">{course.name}</p>
                      <p className="text-[10px] text-muted-foreground font-mono">{course.code}</p>
                    </div>
                    <span className="text-[10px] text-muted-foreground bg-background px-2 py-0.5 rounded-full">
                      {course.semester}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommendation Note */}
            <div className="bg-[var(--cyan)]/30 rounded-xl p-4 border border-[var(--cyan)]/50">
              <p className="text-xs text-foreground leading-relaxed">
                Based on your profile, we recommend prioritizing retake courses and prerequisites
                for your next semester registration.
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
