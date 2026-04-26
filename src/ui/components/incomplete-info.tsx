'use client'

import { AlertCircle, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

interface IncompleteInfoProps {
  onBackToChat?: () => void
}

export function IncompleteInfo({ onBackToChat }: IncompleteInfoProps) {
  return (
    <div className="h-full flex flex-col items-center justify-center px-4 py-8">
      <div className="max-w-sm text-center space-y-6">
        {/* Icon */}
        <div className="mx-auto w-16 h-16 rounded-full bg-[var(--light-pink)]/20 flex items-center justify-center">
          <AlertCircle className="w-8 h-8 text-[var(--light-pink)]" strokeWidth={1.5} />
        </div>

        {/* Message */}
        <div className="space-y-2">
          <h2 className="text-xl font-semibold text-foreground">
            Thông tin chưa đủ
          </h2>
          <p className="text-sm text-muted-foreground">
            Vui lòng cung cấp các thông tin cần thiết trong cửa sổ chat để mình có thể tạo lộ trình học tập cho bạn:
          </p>
        </div>

        {/* Requirements List */}
        <ul className="text-left space-y-2 bg-[var(--muted)]/50 rounded-lg p-4">
          <li className="flex items-start gap-2 text-xs text-muted-foreground">
            <span className="text-[var(--mint)] font-bold mt-0.5">•</span>
            <span>Điểm GPA hiện tại</span>
          </li>
          <li className="flex items-start gap-2 text-xs text-muted-foreground">
            <span className="text-[var(--mint)] font-bold mt-0.5">•</span>
            <span>Số tín chỉ đã hoàn thành</span>
          </li>
          <li className="flex items-start gap-2 text-xs text-muted-foreground">
            <span className="text-[var(--mint)] font-bold mt-0.5">•</span>
            <span>Các môn học lại (nếu có)</span>
          </li>
          <li className="flex items-start gap-2 text-xs text-muted-foreground">
            <span className="text-[var(--mint)] font-bold mt-0.5">•</span>
            <span>Mức độ học tập (nhẹ/vừa/nặng)</span>
          </li>
        </ul>

        {/* Back to Chat Button */}
        {onBackToChat && (
          <Button
            onClick={onBackToChat}
            variant="default"
            size="sm"
            className="w-full"
          >
            <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Quay lại Chat
          </Button>
        )}
      </div>
    </div>
  )
}
