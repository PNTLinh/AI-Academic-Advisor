"use client"

import { useState, useEffect } from "react"
import { Trash2, Plus, MessageSquare } from "lucide-react"
import { format } from "date-fns"
import { vi } from "date-fns/locale"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"

interface ChatHistoryItem {
  id: string
  title: string
  timestamp: Date
  preview: string
}

interface ChatHistorySidebarProps {
  isOpen: boolean
  onClose: () => void
  onSelectChat: (chatId: string) => void
  onNewChat: () => void
  chatHistory: ChatHistoryItem[]
  currentChatId?: string
}

export function ChatHistorySidebar({
  isOpen,
  onClose,
  onSelectChat,
  onNewChat,
  chatHistory,
  currentChatId
}: ChatHistorySidebarProps) {
  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-full w-64 bg-white border-r border-gray-200 z-50 transform transition-transform lg:translate-x-0 lg:static lg:z-auto ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-4 border-b border-gray-200">
            <Button
              onClick={onNewChat}
              className="w-full gap-2"
              size="sm"
            >
              <Plus className="w-4 h-4" />
              Trò chuyện mới
            </Button>
          </div>

          {/* Chat History */}
          <ScrollArea className="flex-1">
            <div className="p-3">
              {chatHistory.length === 0 ? (
                <div className="text-sm text-gray-500 text-center py-8">
                  Chưa có lịch sử chat
                </div>
              ) : (
                <div className="space-y-2">
                  {chatHistory.map((chat) => (
                    <div
                      key={chat.id}
                      onClick={() => {
                        onSelectChat(chat.id)
                        onClose()
                      }}
                      className={`p-3 rounded-lg cursor-pointer transition-colors ${
                        currentChatId === chat.id
                          ? "bg-blue-100 border-l-2 border-blue-500"
                          : "hover:bg-gray-100"
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <MessageSquare className="w-4 h-4 mt-0.5 flex-shrink-0 text-gray-400" />
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-medium text-gray-900 truncate">
                            {chat.title}
                          </h3>
                          <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                            {chat.preview}
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            {format(chat.timestamp, "d MMM, HH:mm", { locale: vi })}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      </aside>
    </>
  )
}
