'use client'

/**
 * Hook for elegant API error handling with toast notifications.
 * Automatically shows user-friendly error messages in Vietnamese without disrupting the UI.
 */

import { useToast } from '@/hooks/use-toast'

interface UseApiErrorReturn {
  handleError: (error: unknown, fallbackMessage?: string) => void
  isNetworkError: (error: unknown) => boolean
  isValidationError: (error: unknown) => boolean
}

export function useApiError(): UseApiErrorReturn {
  const { toast } = useToast()

  const isNetworkError = (error: unknown): boolean => {
    return error instanceof TypeError && error.message.includes('fetch')
  }

  const isValidationError = (error: unknown): boolean => {
    return error instanceof Error && error.message.includes('validation')
  }

  const handleError = (error: unknown, fallbackMessage = 'Có lỗi xảy ra') => {
    let title = 'Lỗi'
    let description = fallbackMessage

    if (error instanceof Error) {
      description = error.message
      
      // Extract server error message if available
      if (description.includes('detail:')) {
        const match = description.match(/detail:\s*"?([^"]*)"?/)
        if (match?.[1]) {
          description = match[1]
        }
      }
    }

    // Categorize error for better UX
    if (isNetworkError(error)) {
      title = 'Lỗi Kết nối'
      description = 'Không thể kết nối tới máy chủ. Vui lòng kiểm tra kết nối mạng.'
    } else if (isValidationError(error)) {
      title = 'Lỗi Xác thực'
    } else if (description.includes('not found')) {
      title = 'Không Tìm Thấy'
    } else if (description.includes('Cannot generate')) {
      title = 'Cần Thiết Lập'
    }

    // Show elegant toast notification
    toast({
      title,
      description,
      variant: 'destructive',
    })

    // Log error for debugging
    console.error(`[${title}]`, error)
  }

  return {
    handleError,
    isNetworkError,
    isValidationError,
  }
}
