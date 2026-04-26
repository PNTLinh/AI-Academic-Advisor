'use client'

import { useCallback, useEffect, useState } from 'react'

const SESSION_STORAGE_KEY = 'sessionId'

/**
 * Generate a simple UUID v4-like string (no external dependency)
 * Format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
 */
function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * Hook to manage session ID (stored in localStorage)
 * - On first load: generate UUID and save to localStorage
 * - On subsequent loads: retrieve from localStorage
 * - Provides sessionId state and re-fetch capability
 */
export function useSession() {
  const [sessionId, setSessionId] = useState<string>('')
  const [isLoading, setIsLoading] = useState(true)

  // Initialize session ID from localStorage or generate new one
  const initializeSession = useCallback(() => {
    setIsLoading(true)
    try {
      // Check if running in browser
      if (typeof window === 'undefined') {
        setIsLoading(false)
        return
      }

      let storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY)

      if (!storedSessionId) {
        // Generate new session ID
        storedSessionId = generateUUID()
        localStorage.setItem(SESSION_STORAGE_KEY, storedSessionId)
        console.log(`✅ New session created: ${storedSessionId}`)
      } else {
        console.log(`✅ Session restored: ${storedSessionId}`)
      }

      setSessionId(storedSessionId)
    } catch (error) {
      console.error('❌ Error initializing session:', error)
      // Fallback: generate inline UUID if localStorage fails
      const fallbackId = generateUUID()
      setSessionId(fallbackId)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Initialize on mount
  useEffect(() => {
    initializeSession()
  }, [initializeSession])

  return {
    sessionId,
    isLoading,
    refreshSession: initializeSession,
  }
}

/**
 * Get session ID synchronously (for use outside components)
 * Falls back to generating UUID if not in browser
 */
export function getSessionId(): string {
  if (typeof window === 'undefined') {
    return generateUUID()
  }

  const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY)
  if (storedSessionId) {
    return storedSessionId
  }

  // Generate and store new session ID
  const newSessionId = generateUUID()
  localStorage.setItem(SESSION_STORAGE_KEY, newSessionId)
  return newSessionId
}

/**
 * Clear session ID (e.g., on logout)
 */
export function clearSessionId(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(SESSION_STORAGE_KEY)
    console.log('🔄 Session cleared')
  }
}
