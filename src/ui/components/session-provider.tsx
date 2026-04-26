'use client'

import React, { ReactNode } from 'react'
import { useSession } from '@/hooks/use-session'

interface SessionContextType {
  sessionId: string
  isLoading: boolean
  refreshSession: () => void
}

const SessionContext = React.createContext<SessionContextType | undefined>(undefined)

export function SessionProvider({ children }: { children: ReactNode }) {
  const session = useSession()

  return (
    <SessionContext.Provider value={session}>
      {children}
    </SessionContext.Provider>
  )
}

export function useSessionContext() {
  const context = React.useContext(SessionContext)
  if (!context) {
    throw new Error('useSessionContext must be used within SessionProvider')
  }
  return context
}
