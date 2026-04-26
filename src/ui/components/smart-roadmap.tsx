"use client"

import { useState } from "react"
import {
  BookOpen,
  Calculator,
  Atom,
  Code,
  Beaker,
  FileText,
  Zap,
  RotateCcw,
  Lightbulb,
  GraduationCap,
  ChevronRight,
} from "lucide-react"

interface Course {
  code: string
  name: string
  credits: number
  priority: "high" | "medium" | "low"
  tag?: string
}

interface Semester {
  id: string
  name: string
  year: string
  status: "current" | "upcoming" | "future"
  courses: Course[]
  totalCredits: number
}

const balancedRoadmap: Semester[] = [
  {
    id: "spring-2024",
    name: "Spring",
    year: "2024",
    status: "current",
    totalCredits: 15,
    courses: [
      { code: "PHYS101", name: "Physics I", credits: 4, priority: "high", tag: "Retake" },
      { code: "MATH301", name: "Linear Algebra", credits: 3, priority: "medium" },
      { code: "CS301", name: "Algorithms", credits: 4, priority: "medium" },
      { code: "STAT201", name: "Statistics I", credits: 4, priority: "low" },
    ],
  },
  {
    id: "summer-2024",
    name: "Summer",
    year: "2024",
    status: "upcoming",
    totalCredits: 6,
    courses: [
      { code: "PHYS102", name: "Physics II", credits: 4, priority: "high", tag: "Retake" },
      { code: "GEN101", name: "Ethics & Society", credits: 2, priority: "low", tag: "Elective" },
    ],
  },
  {
    id: "fall-2024",
    name: "Fall",
    year: "2024",
    status: "future",
    totalCredits: 16,
    courses: [
      { code: "CS401", name: "Software Engineering", credits: 4, priority: "high" },
      { code: "CS402", name: "Database Systems", credits: 4, priority: "medium" },
      { code: "MATH401", name: "Numerical Methods", credits: 3, priority: "medium" },
      { code: "CS403", name: "Computer Networks", credits: 3, priority: "low" },
      { code: "GEN201", name: "Technical Writing", credits: 2, priority: "low", tag: "Elective" },
    ],
  },
  {
    id: "spring-2025",
    name: "Spring",
    year: "2025",
    status: "future",
    totalCredits: 15,
    courses: [
      { code: "CS501", name: "Machine Learning", credits: 4, priority: "high" },
      { code: "CS502", name: "Capstone Project I", credits: 4, priority: "high" },
      { code: "CS404", name: "Operating Systems", credits: 4, priority: "medium" },
      { code: "GEN301", name: "Project Management", credits: 3, priority: "low", tag: "Elective" },
    ],
  },
]

const acceleratedRoadmap: Semester[] = [
  {
    id: "spring-2024",
    name: "Spring",
    year: "2024",
    status: "current",
    totalCredits: 20,
    courses: [
      { code: "PHYS101", name: "Physics I", credits: 4, priority: "high", tag: "Retake" },
      { code: "PHYS102", name: "Physics II", credits: 4, priority: "high", tag: "Retake" },
      { code: "MATH301", name: "Linear Algebra", credits: 3, priority: "medium" },
      { code: "CS301", name: "Algorithms", credits: 4, priority: "medium" },
      { code: "STAT201", name: "Statistics I", credits: 4, priority: "low" },
      { code: "GEN101", name: "Ethics & Society", credits: 2, priority: "low", tag: "Elective" },
    ],
  },
  {
    id: "summer-2024",
    name: "Summer",
    year: "2024",
    status: "upcoming",
    totalCredits: 10,
    courses: [
      { code: "CS401", name: "Software Engineering", credits: 4, priority: "high" },
      { code: "MATH401", name: "Numerical Methods", credits: 3, priority: "medium" },
      { code: "GEN201", name: "Technical Writing", credits: 2, priority: "low", tag: "Elective" },
    ],
  },
  {
    id: "fall-2024",
    name: "Fall",
    year: "2024",
    status: "future",
    totalCredits: 18,
    courses: [
      { code: "CS501", name: "Machine Learning", credits: 4, priority: "high" },
      { code: "CS402", name: "Database Systems", credits: 4, priority: "high" },
      { code: "CS403", name: "Computer Networks", credits: 3, priority: "medium" },
      { code: "CS404", name: "Operating Systems", credits: 4, priority: "medium" },
      { code: "GEN301", name: "Project Management", credits: 3, priority: "low", tag: "Elective" },
    ],
  },
  {
    id: "spring-2025",
    name: "Spring",
    year: "2025",
    status: "future",
    totalCredits: 8,
    courses: [
      { code: "CS502", name: "Capstone Project I", credits: 4, priority: "high" },
      { code: "CS503", name: "Capstone Project II", credits: 4, priority: "high" },
    ],
  },
]

const courseIcons: Record<string, React.ReactNode> = {
  MATH: <Calculator className="w-3.5 h-3.5" strokeWidth={1.5} />,
  PHYS: <Atom className="w-3.5 h-3.5" strokeWidth={1.5} />,
  CS: <Code className="w-3.5 h-3.5" strokeWidth={1.5} />,
  CHEM: <Beaker className="w-3.5 h-3.5" strokeWidth={1.5} />,
  STAT: <FileText className="w-3.5 h-3.5" strokeWidth={1.5} />,
  GEN: <Lightbulb className="w-3.5 h-3.5" strokeWidth={1.5} />,
}

function getCourseIcon(code: string) {
  const prefix = code.replace(/[0-9]/g, "")
  return courseIcons[prefix] || <BookOpen className="w-3.5 h-3.5" strokeWidth={1.5} />
}

const priorityStyles = {
  high: "bg-[var(--priority-high)] text-[#4a2c2f]",
  medium: "bg-[var(--priority-medium)] text-[#4a2c2f]",
  low: "bg-[var(--priority-low)] text-[#1a3a3a]",
}

const statusStyles = {
  current: "border-[var(--mint)] bg-[var(--mint)]/10",
  upcoming: "border-[var(--cyan)] bg-[var(--cyan)]/10",
  future: "border-border bg-card",
}

interface SmartRoadmapProps {
  scenario: "balanced" | "accelerated"
}

export function SmartRoadmap({ scenario }: SmartRoadmapProps) {
  const roadmap = scenario === "balanced" ? balancedRoadmap : acceleratedRoadmap
  const totalCreditsRemaining = roadmap.reduce((acc, sem) => acc + sem.totalCredits, 0)
  const estimatedGraduation = scenario === "balanced" ? "Spring 2025" : "Fall 2024"

  return (
    <div className="h-full flex flex-col">
      {/* Roadmap Stats Header */}
      <div className="flex items-center gap-4 px-4 py-3 bg-card rounded-xl border border-border mb-4">
        <div className="flex items-center gap-2">
          <GraduationCap className="w-5 h-5 text-[var(--mint)]" strokeWidth={1.5} />
          <div>
            <p className="text-xs text-muted-foreground">Est. Graduation</p>
            <p className="text-sm font-semibold text-foreground">{estimatedGraduation}</p>
          </div>
        </div>
        <div className="w-px h-8 bg-border" />
        <div>
          <p className="text-xs text-muted-foreground">Credits Remaining</p>
          <p className="text-sm font-semibold text-foreground">{totalCreditsRemaining} credits</p>
        </div>
        <div className="w-px h-8 bg-border" />
        <div>
          <p className="text-xs text-muted-foreground">Semesters Left</p>
          <p className="text-sm font-semibold text-foreground">{roadmap.length} semesters</p>
        </div>
      </div>

      {/* Scrollable Timeline */}
      <div className="flex-1 overflow-y-auto pr-2 -mr-2">
        <div className="relative pl-6">
          {/* Vertical Timeline Line */}
          <div className="absolute left-[7px] top-4 bottom-4 w-0.5 bg-gradient-to-b from-[var(--mint)] via-[var(--cyan)] to-[var(--light-pink)]" />

          <div className="space-y-4">
            {roadmap.map((semester, index) => (
              <div key={semester.id} className="relative">
                {/* Timeline Node */}
                <div
                  className={`absolute -left-6 top-4 w-3.5 h-3.5 rounded-full border-2 ${
                    semester.status === "current"
                      ? "bg-[var(--mint)] border-[var(--mint)]"
                      : semester.status === "upcoming"
                      ? "bg-[var(--cyan)] border-[var(--cyan)]"
                      : "bg-card border-[var(--light-pink)]"
                  }`}
                />

                {/* Semester Card */}
                <div
                  className={`rounded-xl border-2 p-4 transition-all hover:shadow-md ${statusStyles[semester.status]}`}
                >
                  {/* Semester Header */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-foreground">
                        {semester.name} {semester.year}
                      </h3>
                      {semester.status === "current" && (
                        <span className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-[var(--mint)] text-[#1a3a3a]">
                          Current
                        </span>
                      )}
                    </div>
                    <span className="text-xs font-medium text-muted-foreground">
                      {semester.totalCredits} credits
                    </span>
                  </div>

                  {/* Course List */}
                  <div className="space-y-2">
                    {semester.courses.map((course) => (
                      <div
                        key={course.code}
                        className="flex items-center gap-3 p-2.5 rounded-lg bg-background/60 hover:bg-background transition-colors group"
                      >
                        {/* Course Icon */}
                        <div className="w-7 h-7 rounded-lg bg-[var(--muted)] flex items-center justify-center text-muted-foreground group-hover:text-foreground transition-colors">
                          {getCourseIcon(course.code)}
                        </div>

                        {/* Course Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-muted-foreground">
                              {course.code}
                            </span>
                            {course.tag && (
                              <span
                                className={`px-1.5 py-0.5 text-[9px] font-medium rounded ${
                                  course.tag === "Retake"
                                    ? "bg-[var(--pink)]/30 text-[#4a2c2f]"
                                    : "bg-[var(--cyan)]/30 text-[#1a3a3a]"
                                }`}
                              >
                                {course.tag === "Retake" && (
                                  <RotateCcw className="w-2.5 h-2.5 inline mr-0.5" />
                                )}
                                {course.tag}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-foreground truncate">{course.name}</p>
                        </div>

                        {/* Credits & Priority */}
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">{course.credits}cr</span>
                          <span
                            className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${priorityStyles[course.priority]}`}
                          >
                            {course.priority.charAt(0).toUpperCase() + course.priority.slice(1)}
                          </span>
                        </div>

                        {/* Arrow */}
                        <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
