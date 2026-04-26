'use client'

import { useCallback, useState } from 'react'

interface RoadmapData {
  graduation_path: Record<string, any[]>
  total_semesters: number
  credits_remaining: number
  is_downgraded?: boolean
  warning?: string
  target_cpa?: number
  ai_suggestions?: string[]
}

const ROADMAP_STORAGE_KEY = 'studentRoadmap'

/**
 * Hook to manage roadmap data in localStorage
 * - Save roadmap after fetched from API
 * - Retrieve roadmap from localStorage
 * - Clear roadmap on logout
 */
export function useRoadmapStorage() {
  const [roadmap, setRoadmapState] = useState<RoadmapData | null>(null)

  const saveRoadmap = useCallback((data: RoadmapData) => {
    try {
      if (typeof window !== 'undefined') {
        const payload = {
          data,
          timestamp: Date.now(),
        }
        localStorage.setItem(ROADMAP_STORAGE_KEY, JSON.stringify(payload))
        setRoadmapState(data)
        console.log('✅ Roadmap saved to localStorage')
      }
    } catch (error) {
      console.error('❌ Error saving roadmap:', error)
    }
  }, [])

  const loadRoadmap = useCallback((): RoadmapData | null => {
    try {
      if (typeof window === 'undefined') return null

      const stored = localStorage.getItem(ROADMAP_STORAGE_KEY)
      if (stored) {
        const payload = JSON.parse(stored)
        setRoadmapState(payload.data)
        return payload.data
      }
    } catch (error) {
      console.error('❌ Error loading roadmap:', error)
    }
    return null
  }, [])

  const clearRoadmap = useCallback(() => {
    try {
      if (typeof window !== 'undefined') {
        localStorage.removeItem(ROADMAP_STORAGE_KEY)
        setRoadmapState(null)
        console.log('🔄 Roadmap cleared')
      }
    } catch (error) {
      console.error('❌ Error clearing roadmap:', error)
    }
  }, [])

  return {
    roadmap,
    saveRoadmap,
    loadRoadmap,
    clearRoadmap,
    hasRoadmap: roadmap !== null,
  }
}

/**
 * Get roadmap synchronously (for use outside components)
 */
export function getRoadmapFromStorage(): RoadmapData | null {
  if (typeof window === 'undefined') return null

  try {
    const stored = localStorage.getItem(ROADMAP_STORAGE_KEY)
    if (stored) {
      const payload = JSON.parse(stored)
      return payload.data
    }
  } catch (error) {
    console.error('❌ Error reading roadmap:', error)
  }
  return null
}
