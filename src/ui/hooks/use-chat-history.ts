'use client'

import { useCallback } from 'react'

interface ChatMessage {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const CHAT_HISTORY_KEY = 'chatHistory'

export function useChatHistory() {
  const saveChatMessage = useCallback((message: ChatMessage) => {
    try {
      if (typeof window === 'undefined') return
      
      const messages = getChatHistory()
      messages.push({
        ...message,
        timestamp: new Date(message.timestamp)
      })
      
      // Keep only last 20 messages
      const recentMessages = messages.slice(-20)
      localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(recentMessages))
      console.log('✅ Chat message saved to localStorage')
    } catch (error) {
      console.error('❌ Error saving chat message:', error)
    }
  }, [])

  const getChatHistory = useCallback((): ChatMessage[] => {
    try {
      if (typeof window === 'undefined') return []
      
      const stored = localStorage.getItem(CHAT_HISTORY_KEY)
      if (stored) {
        return JSON.parse(stored)
      }
    } catch (error) {
      console.error('❌ Error loading chat history:', error)
    }
    return []
  }, [])

  const clearChatHistory = useCallback(() => {
    try {
      if (typeof window === 'undefined') return
      
      localStorage.removeItem(CHAT_HISTORY_KEY)
      console.log('✅ Chat history cleared')
    } catch (error) {
      console.error('❌ Error clearing chat history:', error)
    }
  }, [])

  return {
    saveChatMessage,
    getChatHistory,
    clearChatHistory
  }
}

export function getChatHistorySync(): ChatMessage[] {
  if (typeof window === 'undefined') return []
  
  try {
    const stored = localStorage.getItem(CHAT_HISTORY_KEY)
    if (stored) {
      return JSON.parse(stored)
    }
  } catch (error) {
    console.error('❌ Error loading chat history:', error)
  }
  return []
}
