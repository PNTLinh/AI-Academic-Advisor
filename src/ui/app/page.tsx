"use client"

import { useState, useRef, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Bot, Send, Paperclip, Map, AlertTriangle, X, FileText, Image as ImageIcon, LogIn, Menu } from "lucide-react"
import Link from "next/link"
import { ChatMessage } from "@/components/chat-message"
import { StudentProfilePanel } from "@/components/student-profile-panel"
import { LoginPrompt } from "@/components/login-prompt"
import { ChatHistorySidebar } from "@/components/chat-history-sidebar"
import { UnauthorizedWarning } from "@/components/unauthorized-warning"
import { api } from "@/lib/api"
import { useApiError } from "@/hooks/use-api-error"
import { useChatHistory } from "@/hooks/use-chat-history"
import { useSessionChat } from "@/hooks/use-session-chat"

// Mock data removed as per user request. Fallback is handled by backend.
const transcriptData: any[] = []

interface StudentProfile {
  gpa: number
  creditsEarned: number
  totalCredits: number
  failedCourses: { code: string; name: string; semester: string }[]
  standing: "Good" | "Warning" | "Probation"
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
  debugInfo?: string
  attachment?: {
    name: string
    type: "pdf" | "image"
    url: string
  }
}

const MESSAGE_LIMIT = 10;

export default function AdvisorChat() {
  const router = useRouter()
  const [isDataConfirmed, setIsDataConfirmed] = useState(false)
  const [studyGoals, setStudyGoals] = useState<StudyGoalsData | null>(null)
  const [inputValue, setInputValue] = useState("")
  const [dynamicMessages, setDynamicMessages] = useState<Message[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [profile, setProfile] = useState<StudentProfile | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [selectedFile, setSelectedFile] = useState<{ file: File; url?: string } | null>(null)
  const [messageCount, setMessageCount] = useState(0)
  const [showLimitPrompt, setShowLimitPrompt] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [warningDismissed, setWarningDismissed] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const { handleError } = useApiError()
  const { saveChatMessage, getChatHistory } = useChatHistory()
  const { getCurrentSession, addMessageToSession, getAllSessions, newSession } = useSessionChat()

  // Load state from localStorage on mount
  useEffect(() => {
    const savedCount = localStorage.getItem("guest_message_count")
    if (savedCount) setMessageCount(parseInt(savedCount, 10))
    
    const loginStatus = localStorage.getItem("is_logged_in")
    if (loginStatus === "true") setIsLoggedIn(true)

    // Load recent messages
    const history = getChatHistory()
    if (history.length > 0) {
      // Map to UI Message format (Date string to Date object)
      setDynamicMessages(history.map(m => ({
        ...m,
        timestamp: new Date(m.timestamp)
      })))
    }
  }, [getChatHistory])

  const fetchUserStatus = async () => {
    try {
      const data = await api.get<any>("/user/status?student_id=SV001")
      setProfile({
        gpa: data.gpa,
        creditsEarned: data.credits_summary.earned,
        totalCredits: data.credits_summary.total,
        standing: data.gpa >= 2.0 ? "Good" : "Warning",
        failedCourses: data.failed_courses.map((id: string) => ({
          code: id,
          name: id, // Hiện tại backend chỉ trả ID, tạm thời map name = code
          semester: "N/A"
        }))
      })
    } catch (err) {
      handleError(err, "Không thể tải hồ sơ sinh viên của bạn")
    }
  }

  const handleConfirmData = async () => {
    setIsDataConfirmed(true)
    await fetchUserStatus()
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Create entry in UI immediately
    setSelectedFile({ file })
    setIsUploading(true)
    setUploadProgress(10) // Start progress

    const formData = new FormData()
    formData.append("file", file)

    try {
      // Mock progress animation for better UX
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => (prev < 90 ? prev + 10 : prev))
      }, 100)

      const uploadRes = await api.post<{ file_path: string }>("/upload", formData)
      
      clearInterval(progressInterval)
      setUploadProgress(100)
      
      setSelectedFile({ 
        file, 
        url: uploadRes.file_path 
      })
    } catch (err) {
      handleError(err, "Tải lên tệp thất bại")
      setSelectedFile(null)
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  const removeSelectedFile = () => {
    setSelectedFile(null)
    setUploadProgress(0)
  }

  const handleSendMessage = async () => {
    if ((!inputValue.trim() && !selectedFile) || isTyping || isUploading) return

    // 0. Check limit for guest
    if (!isLoggedIn && messageCount >= MESSAGE_LIMIT) {
      setShowLimitPrompt(true)
      return
    }

    const userMessageContent = inputValue
    const uploadedFile = selectedFile
    
    setInputValue("")
    setSelectedFile(null)
    setUploadProgress(0)
    setIsTyping(true)

    let attachmentInfo = undefined

    try {
      // 1. Check if we have an uploaded file
      if (uploadedFile && uploadedFile.url) {
        attachmentInfo = {
          name: uploadedFile.file.name,
          type: uploadedFile.file.type.includes("pdf") ? "pdf" : "image" as "pdf" | "image",
          url: uploadedFile.url
        }
      }

      // 2. Add user message to UI
      const userMessage: Message = {
        id: Date.now().toString(),
        type: "user",
        content: userMessageContent,
        timestamp: new Date(),
        attachment: attachmentInfo
      }
      setDynamicMessages((prev) => [...prev, userMessage])
      
      // Save to session (guests) or history (logged-in)
      if (!isLoggedIn) {
        addMessageToSession({
          id: userMessage.id,
          type: 'user',
          content: userMessageContent,
          timestamp: userMessage.timestamp
        })
      } else {
        saveChatMessage({
          id: userMessage.id,
          type: 'user',
          content: userMessageContent,
          timestamp: userMessage.timestamp
        })
      }

      // Update message count for guest
      if (!isLoggedIn) {
        const newCount = messageCount + 1
        setMessageCount(newCount)
        localStorage.setItem("guest_message_count", newCount.toString())
      }

      // 3. Call Real API
      const response = await api.post<{ reply: string; debug_info?: string }>("/chat", {
        message: userMessageContent || (attachmentInfo ? `Uploaded file: ${attachmentInfo.name}` : ""),
        max_turns: 10,
      })

      const aiMessage: Message = {
        id: Date.now().toString(),
        type: "assistant",
        content: response.reply,
        timestamp: new Date(),
        debugInfo: response.debug_info
      }

      setDynamicMessages((prev) => [...prev, aiMessage])
      
      // Save to session (guests) or history (logged-in)
      if (!isLoggedIn) {
        addMessageToSession({
          id: aiMessage.id,
          type: 'assistant',
          content: response.reply,
          timestamp: aiMessage.timestamp
        })
      } else {
        saveChatMessage({
          id: aiMessage.id,
          type: 'assistant',
          content: response.reply,
          timestamp: aiMessage.timestamp
        })
      }
    } catch (error) {
      handleError(error, "Không thể gửi tin nhắn tới cố vấn")
      const errorMessage: Message = {
        id: Date.now().toString(),
        type: "assistant",
        content: "Hệ thống gặp sự cố. Vui lòng thử lại sau.",
        timestamp: new Date(),
        debugInfo: String(error)
      }
      setDynamicMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsTyping(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleMockLogin = () => {
    setIsLoggedIn(true)
    localStorage.setItem("is_logged_in", "true")
    setShowLimitPrompt(false)
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="h-screen flex flex-col lg:flex-row">
        {/* Chat History Sidebar - Only for logged-in users */}
        {isLoggedIn && (
          <ChatHistorySidebar
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            onSelectChat={(chatId) => {
              // TODO: Load chat from history
            }}
            onNewChat={() => {
              setDynamicMessages([])
              newSession()
            }}
            chatHistory={getAllSessions().map(session => ({
              id: session.id,
              title: session.title,
              timestamp: session.updatedAt,
              preview: session.messages.map(m => m.content).join(" ")
            }))}
          />
        )}

        {/* Chat Window */}
        <div className="flex-1 flex flex-col lg:border-r lg:border-border">
          {/* Chat Header */}
          <header className="px-4 sm:px-6 py-4 border-b border-border bg-card">
            <div className="flex items-center gap-3">
              {isLoggedIn && (
                <button
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="lg:hidden p-1 hover:bg-border rounded-lg"
                >
                  <Menu className="w-5 h-5" />
                </button>
              )}
              <div className="w-10 h-10 rounded-xl bg-[var(--mint)] flex items-center justify-center">
                <Bot className="w-5 h-5 text-[#1a3a3a]" strokeWidth={1.5} />
              </div>
              <div>
                <h1 className="font-semibold text-foreground">Trợ lý Tư vấn Học tập AI</h1>
                <p className="text-xs text-muted-foreground">Cố vấn Phân tích Bảng điểm</p>
              </div>
              <div className="ml-auto flex items-center gap-3">
                <Link
                  href="/planner"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--light-pink)] hover:bg-[var(--pink)] text-[#4a2c2f] text-xs font-medium transition-colors"
                >
                  <Map className="w-3.5 h-3.5" strokeWidth={1.5} />
                  <span className="hidden sm:inline">Xem lộ trình</span>
                </Link>
                <div className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${isLoggedIn ? "bg-[#34d399]" : "bg-[var(--mint)]"} animate-pulse`} />
                  <span className="text-xs text-muted-foreground">{isLoggedIn ? "Thành viên" : "Khách"}</span>
                </div>
              </div>
            </div>
          </header>

          {/* Unauthorized Warning - Only for guests */}
          {!isLoggedIn && (
            <div className="px-4 sm:px-6 py-4 border-b border-border">
              <UnauthorizedWarning 
                onDismiss={() => setWarningDismissed(true)}
                isDismissed={warningDismissed}
              />
            </div>
          )}

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6" id="chat-messages-container">
            <div className="max-w-2xl mx-auto space-y-4">
              {/* Assistant greeting */}
              <ChatMessage
                type="assistant"
                content="Chào bạn! Mình là Trợ lý Tư vấn Học tập AI. Bạn hãy tải lên bảng điểm tập trung để mình giúp bạn phân tích lộ trình học tập nhé."
              />

              {/* Dynamic messages from user input and API responses */}
              {dynamicMessages.map((message) => (
                <ChatMessage
                  key={message.id}
                  type={message.type}
                  content={message.content}
                  debugInfo={message.debugInfo}
                  attachment={message.attachment}
                />
              ))}

              {isTyping && (
                <ChatMessage
                  type="assistant"
                  content="..."
                  isTyping={true}
                />
              )}
            </div>
          </div>

          {/* Chat Input */}
          <div className="px-4 sm:px-6 py-4 border-t border-border bg-card">
            <div className="max-w-2xl mx-auto">
              
              {/* File Preview Bar */}
              {selectedFile && (
                <div className="mb-3 flex flex-col gap-2 p-3 rounded-xl bg-[var(--muted)] border border-border animate-in slide-in-from-bottom-2 duration-300">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-[var(--cyan)]/30 flex items-center justify-center flex-shrink-0">
                      {selectedFile.file.type.includes("image") ? (
                        <ImageIcon className="w-5 h-5 text-[#1a3a3a]" strokeWidth={1.5} />
                      ) : (
                        <FileText className="w-5 h-5 text-[#1a3a3a]" strokeWidth={1.5} />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-foreground truncate">{selectedFile.file.name}</p>
                      <p className="text-[10px] text-muted-foreground uppercase">
                        {(selectedFile.file.size / 1024).toFixed(1)} KB • {isUploading ? "Đang tải lên..." : "Đã tải lên"}
                      </p>
                    </div>
                    <button 
                      onClick={removeSelectedFile}
                      className="w-8 h-8 rounded-full hover:bg-border flex items-center justify-center transition-colors"
                    >
                      <X className="w-4 h-4 text-muted-foreground" />
                    </button>
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="w-full h-1 bg-border rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-[var(--mint)] transition-all duration-300 ease-out" 
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              <div 
                className={`flex items-center gap-2 bg-[var(--muted)] rounded-2xl px-4 py-2 relative border-2 ${!isLoggedIn && messageCount >= MESSAGE_LIMIT ? "border-[var(--mint)]/30 cursor-pointer" : "border-transparent"}`}
                onClick={() => {
                  if (!isLoggedIn && messageCount >= MESSAGE_LIMIT) {
                    setShowLimitPrompt(true)
                  }
                }}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  className="hidden"
                  accept=".pdf,.png,.jpg"
                />
                <button 
                  onClick={(e) => {
                    e.stopPropagation()
                    fileInputRef.current?.click()
                  }}
                  disabled={isUploading || (!isLoggedIn && messageCount >= MESSAGE_LIMIT)}
                  className="w-8 h-8 rounded-lg hover:bg-border flex items-center justify-center transition-colors disabled:opacity-50"
                >
                  <Paperclip className={`w-4 h-4 ${isUploading ? "animate-pulse" : "text-muted-foreground"}`} strokeWidth={1.5} />
                </button>
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={!isLoggedIn && messageCount >= MESSAGE_LIMIT ? "Đăng nhập để nhận tư vấn không giới hạn..." : "Nhập tin nhắn hoặc tải lên bảng điểm..."}
                  disabled={!isLoggedIn && messageCount >= MESSAGE_LIMIT}
                  className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none disabled:cursor-pointer"
                />
                
                {!isLoggedIn && messageCount >= MESSAGE_LIMIT ? (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setShowLimitPrompt(true)
                    }}
                    className="px-3 py-1.5 rounded-lg bg-[var(--mint)] hover:bg-[#6bcbca] text-[#1a3a3a] text-xs font-semibold transition-colors flex items-center gap-1"
                  >
                    <LogIn className="w-3.5 h-3.5" />
                    Đăng nhập ngay
                  </button>
                ) : (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleSendMessage()
                    }}
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
                )}

                {!isLoggedIn && messageCount > 0 && messageCount < MESSAGE_LIMIT && (
                  <div className="absolute -top-6 right-0 text-[10px] text-muted-foreground font-medium">
                    Còn <span className="text-[var(--mint)]">{MESSAGE_LIMIT - messageCount}</span> lượt tư vấn miễn phí
                  </div>
                )}
              </div>
              <p className="text-[10px] text-center text-muted-foreground mt-2">
                Phản hồi từ AI chỉ mang tính chất tham khảo. Hãy tham vấn cố vấn học tập để có quyết định chính thức.
              </p>
            </div>
          </div>
        </div>

        {/* Student Profile Panel */}
        <aside className="hidden lg:block w-80 xl:w-96 p-4 bg-background">
          <StudentProfilePanel 
            profile={profile || { gpa: 0, creditsEarned: 0, totalCredits: 132, failedCourses: [], standing: "Good" }} 
            isDataConfirmed={isDataConfirmed} 
          />
        </aside>
      </div>

      {/* Limit Prompt */}
      {showLimitPrompt && (
        <LoginPrompt 
          title="Giới hạn tư vấn miễn phí"
          description="Bạn đã hết lượt tư vấn miễn phí cho khách. Vui lòng đăng nhập để tiếp tục trò chuyện và lưu lại lộ trình học tập của mình."
          onDismiss={() => setShowLimitPrompt(false)}
          onLoginClick={() => router.push("/login")}
          onSignupClick={() => router.push("/signup")}
          showDownload={false}
        />
      )}
    </main>
  )
}
