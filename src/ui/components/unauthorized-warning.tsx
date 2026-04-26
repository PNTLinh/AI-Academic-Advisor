"use client"

import { AlertTriangle, X } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"

interface UnauthorizedWarningProps {
  onDismiss: () => void
  isDismissed?: boolean
}

export function UnauthorizedWarning({ onDismiss, isDismissed }: UnauthorizedWarningProps) {
  if (isDismissed) return null

  return (
    <div className="bg-amber-50 border-l-4 border-amber-400 p-4 mb-4 rounded">
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-semibold text-amber-900">
            ⚠️ Bạn chưa đăng nhập
          </h3>
          <p className="text-sm text-amber-800 mt-1">
            Nếu bạn đóng tab trình duyệt, toàn bộ lịch sử trò chuyện sẽ bị xóa. 
            <strong className="block mt-1">Hãy đăng nhập để lưu trữ lịch sử chat vĩnh viễn.</strong>
          </p>
          <div className="flex gap-2 mt-3">
            <Link href="/login">
              <Button size="sm" variant="default">
                Đăng nhập
              </Button>
            </Link>
            <Link href="/signup">
              <Button size="sm" variant="outline">
                Đăng ký
              </Button>
            </Link>
          </div>
        </div>
        <button
          onClick={onDismiss}
          className="text-amber-600 hover:text-amber-700 flex-shrink-0"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}
