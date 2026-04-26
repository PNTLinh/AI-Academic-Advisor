'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'
import { api } from '@/lib/api'

export default function SignupPage() {
  const router = useRouter()
  
  // Step 1: Registration Request
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Step 2: OTP Verification
  const [step, setStep] = useState<'register' | 'verify'>('register')
  const [otp, setOtp] = useState('')
  const [otpLoading, setOtpLoading] = useState(false)

  const handleRegisterRequest = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // Validate inputs
      if (!email || !password || !confirmPassword || !displayName) {
        throw new Error('Vui lòng điền đầy đủ thông tin')
      }

      if (password !== confirmPassword) {
        throw new Error('Mật khẩu xác nhận không khớp')
      }

      if (password.length < 6) {
        throw new Error('Mật khẩu phải có ít nhất 6 ký tự')
      }

      if (displayName.length < 2) {
        throw new Error('Tên hiển thị phải có ít nhất 2 ký tự')
      }

      // Send registration request
      const response = await api.post('/auth/register-request', { email, password, display_name: displayName })

      // Move to OTP verification step
      setStep('verify')
      setError('')
    } catch (err: any) {
      setError(err.message || 'Đăng ký thất bại. Vui lòng thử lại.')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setOtpLoading(true)

    try {
      if (!otp) {
        throw new Error('Vui lòng nhập mã OTP')
      }

      // Verify OTP
      const response = await api.post('/auth/verify-otp', { email, otp })

      // Store token
      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('user_id', response.user_id)
      localStorage.setItem('email', response.email)

      // Show success and redirect
      setTimeout(() => {
        router.push('/planner')
      }, 1000)
    } catch (err: any) {
      setError(err.message || 'Xác minh OTP thất bại. Vui lòng thử lại.')
    } finally {
      setOtpLoading(false)
    }
  }

  const handleBackToRegister = () => {
    setStep('register')
    setOtp('')
    setError('')
  }

  return (
    <main className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          {/* Logo */}
          <div className="w-16 h-16 rounded-2xl bg-[var(--mint)] flex items-center justify-center mx-auto mb-4">
            <div className="text-2xl font-bold text-[#1a3a3a]">AA</div>
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-foreground">Đăng ký</h1>
          <p className="text-sm text-muted-foreground mt-2">
            {step === 'register' 
              ? 'Tạo tài khoản mới để lưu kế hoạch học tập'
              : 'Xác minh email của bạn'
            }
          </p>
        </div>

        <Card>
          {step === 'register' ? (
            // ─── Registration Step ───
            <>
              <CardHeader>
                <CardTitle>Tạo tài khoản</CardTitle>
                <CardDescription>
                  Bước 1: Nhập thông tin tài khoản
                </CardDescription>
              </CardHeader>

              <CardContent>
                <form onSubmit={handleRegisterRequest} className="space-y-4">
                  {/* Display Name */}
                  <div className="space-y-2">
                    <label htmlFor="displayName" className="block text-sm font-medium">
                      Tên hiển thị
                    </label>
                    <Input
                      id="displayName"
                      type="text"
                      placeholder="Tên của bạn"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      disabled={loading}
                      required
                    />
                  </div>

                  {/* Email */}
                  <div className="space-y-2">
                    <label htmlFor="email" className="block text-sm font-medium">
                      Email
                    </label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="your@email.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      disabled={loading}
                      required
                    />
                  </div>

                  {/* Password */}
                  <div className="space-y-2">
                    <label htmlFor="password" className="block text-sm font-medium">
                      Mật khẩu
                    </label>
                    <Input
                      id="password"
                      type="password"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      disabled={loading}
                      required
                    />
                    <p className="text-xs text-muted-foreground">
                      Ít nhất 6 ký tự
                    </p>
                  </div>

                  {/* Confirm Password */}
                  <div className="space-y-2">
                    <label htmlFor="confirm" className="block text-sm font-medium">
                      Xác nhận mật khẩu
                    </label>
                    <Input
                      id="confirm"
                      type="password"
                      placeholder="••••••••"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      disabled={loading}
                      required
                    />
                  </div>

                  {/* Error Message */}
                  {error && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  {/* Submit Button */}
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={loading || !email || !password || !confirmPassword || !displayName}
                  >
                    {loading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Đang gửi mã...
                      </>
                    ) : (
                      'Tiếp tục'
                    )}
                  </Button>
                </form>

                {/* Login link */}
                <div className="mt-4 text-center text-sm text-muted-foreground">
                  Đã có tài khoản?{' '}
                  <Link href="/login" className="text-primary hover:underline font-medium">
                    Đăng nhập
                  </Link>
                </div>
              </CardContent>
            </>
          ) : (
            // ─── OTP Verification Step ───
            <>
              <CardHeader>
                <CardTitle>Xác minh email</CardTitle>
                <CardDescription>
                  Bước 2: Nhập mã OTP đã gửi đến {email}
                </CardDescription>
              </CardHeader>

              <CardContent>
                <form onSubmit={handleVerifyOTP} className="space-y-4">
                  {/* OTP Code */}
                  <div className="space-y-2">
                    <label htmlFor="otp" className="block text-sm font-medium">
                      Mã OTP
                    </label>
                    <Input
                      id="otp"
                      type="text"
                      placeholder="000000"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      disabled={otpLoading}
                      maxLength={6}
                      required
                    />
                    <p className="text-xs text-muted-foreground">
                      Mã 6 chữ số đã gửi đến email của bạn. Hết hạn trong 15 phút.
                    </p>
                  </div>

                  {/* Error Message */}
                  {error && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  {/* Submit Button */}
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={otpLoading || otp.length < 6}
                  >
                    {otpLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Đang xác minh...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Xác minh
                      </>
                    )}
                  </Button>

                  {/* Back Button */}
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={handleBackToRegister}
                    disabled={otpLoading}
                  >
                    Quay lại
                  </Button>
                </form>

                {/* Resend info */}
                <div className="mt-4 text-center text-sm text-muted-foreground">
                  Không nhận được mã?{' '}
                  <button
                    onClick={handleBackToRegister}
                    className="text-primary hover:underline font-medium"
                  >
                    Gửi lại
                  </button>
                </div>
              </CardContent>
            </>
          )}
        </Card>
      </div>
    </main>
  )
}
