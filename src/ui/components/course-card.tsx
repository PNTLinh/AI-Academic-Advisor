"use client"

import { BookOpen, Calculator, Atom, Code, FlaskConical, Globe } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

export type Priority = "high" | "medium" | "low"

export interface Course {
  id: string
  name: string
  credits: number
  priority: Priority
  description: string
  icon: "math" | "physics" | "programming" | "chemistry" | "languages" | "general"
}

const iconMap = {
  math: Calculator,
  physics: Atom,
  programming: Code,
  chemistry: FlaskConical,
  languages: Globe,
  general: BookOpen,
}

const priorityConfig = {
  high: {
    label: "High",
    className: "bg-[var(--priority-high)] text-[#4a2c2f]",
  },
  medium: {
    label: "Medium",
    className: "bg-[var(--priority-medium)] text-[#4a2c2f]",
  },
  low: {
    label: "Low",
    className: "bg-[var(--priority-low)] text-[#1a3a3a]",
  },
}

interface CourseCardProps {
  course: Course
}

export function CourseCard({ course }: CourseCardProps) {
  const Icon = iconMap[course.icon]
  const priority = priorityConfig[course.priority]

  return (
    <Card className="group border-0 shadow-sm hover:shadow-md transition-all duration-300 bg-card overflow-hidden">
      <CardContent className="p-5">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-[var(--mint)]/20 flex items-center justify-center group-hover:bg-[var(--mint)]/30 transition-colors">
            <Icon className="w-6 h-6 text-[var(--mint)]" strokeWidth={1.5} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-3 mb-2">
              <h3 className="font-semibold text-card-foreground truncate">{course.name}</h3>
              <span
                className={cn(
                  "flex-shrink-0 px-2.5 py-1 rounded-full text-xs font-medium",
                  priority.className
                )}
              >
                {priority.label}
              </span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">{course.description}</p>
            <div className="mt-3 flex items-center gap-2">
              <span className="text-xs font-medium px-2 py-0.5 rounded-md bg-[var(--cyan)]/30 text-muted-foreground">
                {course.credits} credits
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
