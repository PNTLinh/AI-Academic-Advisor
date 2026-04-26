"use client"

import { useState } from "react"
import { Bot, Send, Paperclip, Map } from "lucide-react"
import Link from "next/link"
import { ChatMessage } from "@/components/chat-message"
import { StudentProfilePanel } from "@/components/student-profile-panel"

const transcriptData = [
  { code: "MATH201", name: "Calculus I", grade: "B+", credits: 4 },
  { code: "PHYS101", name: "Physics I", grade: "F", credits: 4 },
  { code: "CS101", name: "Intro to Programming", grade: "A", credits: 3 },
  { code: "CHEM101", name: "General Chemistry", grade: "C+", credits: 3 },
  { code: "ENG101", name: "English Composition", grade: "A-", credits: 3 },
  { code: "MATH202", name: "Calculus II", grade: "C", credits: 4 },
  { code: "CS201", name: "Data Structures", grade: "B", credits: 3 },
  { code: "PHYS102", name: "Physics II", grade: "F", credits: 4 },
]

const studentProfile = {
  gpa: 2.67,
  creditsEarned: 72,
  totalCredits: 120,
  standing: "Warning" as const,
  failedCourses: [
    { code: "PHYS101", name: "Physics I", semester: "2023.1" },
    { code: "PHYS102", name: "Physics II", semester: "2023.2" },
  ],
}

interface StudyGoalsData {
  effort: string
  blackoutSlots: string[]
}

interface Message {
  id: string
  type: "user" | "assistant"
  content: string
  timestamp: Date
}

export default function AdvisorChat() {
  const [isDataConfirmed, setIsDataConfirmed] = useState(false)
  const [studyGoals, setStudyGoals] = useState<StudyGoalsData | null>(null)
  const [inputValue, setInputValue] = useState("")
  const [dynamicMessages, setDynamicMessages] = useState<Message[]>([])

  const handleConfirmData = () => {
    setIsDataConfirmed(true)
  }

  const handleStudyGoalsComplete = (data: StudyGoalsData) => {
    setStudyGoals(data)
  }

  const handleSendMessage = () => {
    if (!inputValue.trim()) return

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: inputValue,
      timestamp: new Date(),
    }

    setDynamicMessages((prev) => [...prev, userMessage])
    setInputValue("")

    // Simulate AI response after a short delay
    setTimeout(() => {
      const aiResponses = [
        "Thank you for your message. This feature is currently under development. Please wait for the backend integration.",
        "I understand your question. The AI advisor is being developed and will be available soon.",
        "That's a great question! Once the backend is connected, I'll be able to provide personalized recommendations based on your transcript.",
        "I appreciate your input. The chat functionality is in beta. For now, you can use the roadmap planner to explore your course options.",
      ]

      const randomResponse = aiResponses[Math.floor(Math.random() * aiResponses.length)]

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "assistant",
        content: randomResponse,
        timestamp: new Date(),
      }

      setDynamicMessages((prev) => [...prev, aiMessage])
    }, 500)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const getEffortLabel = (effort: string) => {
    switch (effort) {
      case "light":
        return "Light (12-15 credits)"
      case "standard":
        return "Standard (15-18 credits)"
      case "accelerated":
        return "Accelerated (18-22 credits)"
      default:
        return effort
    }
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="h-screen flex flex-col lg:flex-row">
        {/* Chat Window */}
        <div className="flex-1 flex flex-col lg:border-r lg:border-border">
          {/* Chat Header */}
          <header className="px-4 sm:px-6 py-4 border-b border-border bg-card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[var(--mint)] flex items-center justify-center">
                <Bot className="w-5 h-5 text-[#1a3a3a]" strokeWidth={1.5} />
              </div>
              <div>
                <h1 className="font-semibold text-foreground">Academic Advisor AI</h1>
                <p className="text-xs text-muted-foreground">Transcript Analysis Assistant</p>
              </div>
              <div className="ml-auto flex items-center gap-3">
                <Link
                  href="/planner"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--light-pink)] hover:bg-[var(--pink)] text-[#4a2c2f] text-xs font-medium transition-colors"
                >
                  <Map className="w-3.5 h-3.5" strokeWidth={1.5} />
                  <span className="hidden sm:inline">View Roadmap</span>
                </Link>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[var(--mint)] animate-pulse" />
                  <span className="text-xs text-muted-foreground">Online</span>
                </div>
              </div>
            </div>
          </header>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
            <div className="max-w-2xl mx-auto space-y-4">
              {/* Assistant greeting */}
              <ChatMessage
                type="assistant"
                content="Hello! I'm your Academic Advisor AI. Upload your transcript and I'll help you analyze your academic progress and plan your next semester."
              />

              {/* User uploads PDF */}
              <ChatMessage
                type="user"
                content="Here's my transcript from the university portal."
                attachment={{ name: "Academic_Transcript_2024.pdf", type: "pdf" }}
              />

              {/* Assistant response with table */}
              <ChatMessage
                type="assistant"
                content="I've analyzed your transcript. Here's the extracted course data. Please review and confirm if the information is correct:"
                transcriptData={transcriptData}
                onConfirmData={handleConfirmData}
                isConfirmed={isDataConfirmed}
              />

              {isDataConfirmed && (
                <>
                  <ChatMessage
                    type="assistant"
                    content="Data confirmed. I've updated your Student Persona profile on the right panel. Based on your transcript, I noticed you have 2 failed Physics courses. I recommend prioritizing these retakes in your next semester."
                  />
                  <ChatMessage
                    type="assistant"
                    content="How do you want to balance your studies this semester?"
                    showStudyGoals
                    onStudyGoalsComplete={handleStudyGoalsComplete}
                  />
                </>
              )}

              {studyGoals && (
                <ChatMessage
                  type="assistant"
                  content={`Perfect! I've recorded your preferences: ${getEffortLabel(studyGoals.effort)} workload with ${studyGoals.blackoutSlots.length} blocked time slots. I'll now generate a personalized study cart that works around your schedule. Would you like me to proceed with course recommendations?`}
                />
              )}

              {/* Dynamic messages from user input */}
              {dynamicMessages.map((message) => (
                <ChatMessage
                  key={message.id}
                  type={message.type}
                  content={message.content}
                />
              ))}
            </div>
          </div>

          {/* Chat Input */}
          <div className="px-4 sm:px-6 py-4 border-t border-border bg-card">
            <div className="max-w-2xl mx-auto">
              <div className="flex items-center gap-2 bg-[var(--muted)] rounded-2xl px-4 py-2">
                <button className="w-8 h-8 rounded-lg hover:bg-border flex items-center justify-center transition-colors">
                  <Paperclip className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} />
                </button>
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type a message or upload a file..."
                  className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none"
                />
                <button
                  onClick={handleSendMessage}
                  className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${inputValue
                      ? "bg-[var(--mint)] hover:bg-[#6bcbca]"
                      : "bg-border cursor-not-allowed"
                    }`}
                  disabled={!inputValue}
                >
                  <Send
                    className={`w-4 h-4 ${inputValue ? "text-[#1a3a3a]" : "text-muted-foreground"}`}
                    strokeWidth={1.5}
                  />
                </button>
              </div>
              <p className="text-[10px] text-center text-muted-foreground mt-2">
                AI responses are for guidance only. Consult your academic advisor for official decisions.
              </p>
            </div>
          </div>
        </div>

        {/* Student Profile Panel */}
        <aside className="hidden lg:block w-80 xl:w-96 p-4 bg-background">
          <StudentProfilePanel profile={studentProfile} isDataConfirmed={isDataConfirmed} />
        </aside>
      </div>
    </main>
  )
}
