/**
 * Session-based chat history for guests
 * Uses sessionStorage - cleared when tab closes
 */
import { useEffect, useState } from 'react'

export interface ChatSession {
  id: string
  title: string
  messages: Array<{
    id: string
    type: 'user' | 'assistant'
    content: string
    timestamp: Date
  }>
  createdAt: Date
  updatedAt: Date
}

const SESSION_KEY = 'chat_session_'
const CURRENT_SESSION_KEY = 'current_session_id'

export function useSessionChat() {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)

  // Initialize session on mount
  useEffect(() => {
    const stored = sessionStorage.getItem(CURRENT_SESSION_KEY)
    if (stored) {
      setCurrentSessionId(stored)
    } else {
      const newId = Date.now().toString()
      sessionStorage.setItem(CURRENT_SESSION_KEY, newId)
      sessionStorage.setItem(SESSION_KEY + newId, JSON.stringify({
        id: newId,
        title: 'Trò chuyện',
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }))
      setCurrentSessionId(newId)
    }
  }, [])

  const getCurrentSession = (): ChatSession | null => {
    if (!currentSessionId) return null
    const stored = sessionStorage.getItem(SESSION_KEY + currentSessionId)
    if (!stored) return null
    const session = JSON.parse(stored)
    return {
      ...session,
      messages: session.messages.map((m: any) => ({
        ...m,
        timestamp: new Date(m.timestamp)
      })),
      createdAt: new Date(session.createdAt),
      updatedAt: new Date(session.updatedAt)
    }
  }

  const addMessageToSession = (message: { id: string; type: 'user' | 'assistant'; content: string; timestamp: Date }) => {
    if (!currentSessionId) return
    const session = getCurrentSession()
    if (!session) return

    session.messages.push(message)
    session.updatedAt = new Date()
    
    // Auto-set title from first user message
    if (session.messages.length === 1 && message.type === 'user') {
      session.title = message.content.substring(0, 50)
    }

    sessionStorage.setItem(SESSION_KEY + currentSessionId, JSON.stringify({
      ...session,
      createdAt: session.createdAt.toISOString(),
      updatedAt: session.updatedAt.toISOString()
    }))
  }

  const getAllSessions = (): ChatSession[] => {
    const sessions: ChatSession[] = []
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i)
      if (key?.startsWith(SESSION_KEY)) {
        const stored = sessionStorage.getItem(key)
        if (stored) {
          const session = JSON.parse(stored)
          sessions.push({
            ...session,
            messages: session.messages.map((m: any) => ({
              ...m,
              timestamp: new Date(m.timestamp)
            })),
            createdAt: new Date(session.createdAt),
            updatedAt: new Date(session.updatedAt)
          })
        }
      }
    }
    return sessions.sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime())
  }

  const newSession = () => {
    const newId = Date.now().toString()
    sessionStorage.setItem(SESSION_KEY + newId, JSON.stringify({
      id: newId,
      title: 'Trò chuyện',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }))
    sessionStorage.setItem(CURRENT_SESSION_KEY, newId)
    setCurrentSessionId(newId)
  }

  return {
    currentSessionId,
    getCurrentSession,
    addMessageToSession,
    getAllSessions,
    newSession
  }
}
