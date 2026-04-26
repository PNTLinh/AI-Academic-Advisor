'use client'

import { LogIn, UserPlus, Download, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useState } from 'react'

interface LoginPromptProps {
  onDismiss?: () => void
  onLoginClick?: () => void
  onSignupClick?: () => void
  onDownloadClick?: () => void
  title?: string
  description?: string
  showDownload?: boolean
}

export function LoginPrompt({
  onDismiss,
  onLoginClick,
  onSignupClick,
  onDownloadClick,
  title = "Lưu kế hoạch của bạn",
  description = "Đăng nhập để lưu kế hoạch học tập vĩnh viễn và nhận tư vấn cá nhân hóa",
  showDownload = true,
}: LoginPromptProps) {
  const [dismissed, setDismissed] = useState(false)

  const handleDismiss = () => {
    setDismissed(true)
    onDismiss?.()
  }

  if (dismissed) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50 print:hidden">
      <div className="bg-card rounded-2xl border border-border shadow-lg max-w-sm w-full p-6 space-y-6">
        {/* Close Button */}
        <div className="flex justify-end">
          <button
            onClick={handleDismiss}
            className="p-1 hover:bg-[var(--muted)] rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-muted-foreground" strokeWidth={1.5} />
          </button>
        </div>

        {/* Header */}
        <div className="space-y-2 text-center">
          <h2 className="text-lg font-semibold text-foreground">
            {title}
          </h2>
          <p className="text-sm text-muted-foreground">
            {description}
          </p>
        </div>

        {/* Buttons */}
        <div className="space-y-3">
          <Button
            onClick={() => {
              onLoginClick?.()
              handleDismiss()
            }}
            className="w-full bg-[var(--mint)] hover:bg-[#6bcbca] text-[#1a3a3a]"
          >
            <LogIn className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Đăng nhập
          </Button>

          <Button
            onClick={() => {
              onSignupClick?.()
              handleDismiss()
            }}
            variant="outline"
            className="w-full"
          >
            <UserPlus className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Đăng ký
          </Button>

          {showDownload && (
            <Button
              onClick={() => {
                onDownloadClick?.()
                handleDismiss()
              }}
              variant="ghost"
              className="w-full text-muted-foreground hover:text-foreground"
            >
              <Download className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Tải xuống PDF
            </Button>
          )}
        </div>

        {/* Footer */}
        <p className="text-xs text-center text-muted-foreground">
          Đã có tài khoản?{' '}
          <button
            onClick={() => {
              onLoginClick?.()
              handleDismiss()
            }}
            className="text-[var(--mint)] hover:underline font-medium"
          >
            Đăng nhập ngay
          </button>
        </p>

        {/* Dismiss Link */}
        <button
          onClick={handleDismiss}
          className="w-full text-xs text-muted-foreground hover:text-foreground transition-colors py-2"
        >
          Bỏ qua lúc này
        </button>
      </div>
    </div>
  )
}
