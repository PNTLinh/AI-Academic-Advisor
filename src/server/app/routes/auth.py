"""Authentication routes with OTP verification."""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr, validator
import secrets, hashlib, os, jwt, re, logging, smtplib
from datetime import datetime, timedelta, timezone
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..dependencies import get_academic_tools

router = APIRouter()
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
ALGORITHM = "HS256"
TOKEN_EXPIRE = 1440  # 24 hours
REFRESH_TOKEN_EXPIRE = 10080  # 7 days
OTP_EXPIRE = 15  # 15 minutes
MAX_LOGIN_ATTEMPTS = 5
ATTEMPT_WINDOW = 15  # minutes

# Email config
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_ENABLED = bool(EMAIL_USER and EMAIL_PASSWORD)
DEV_MODE = os.getenv("AUTH_DEV_MODE", "false").lower() == "true"  # Disable rate limiting


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str
    
    @validator('email')
    def validate_email(cls, v):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Email không hợp lệ')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Mật khẩu phải ≥ 8 ký tự')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Mật khẩu phải có ít nhất 1 chữ hoa')
        if not re.search(r'[a-z]', v):
            raise ValueError('Mật khẩu phải có ít nhất 1 chữ thường')
        if not re.search(r'[0-9]', v):
            raise ValueError('Mật khẩu phải có ít nhất 1 chữ số')
        return v
    
    @validator('display_name')
    def validate_display_name(cls, v):
        if len(v) < 2 or len(v) > 100:
            raise ValueError('Tên phải 2-100 ký tự')
        if not re.match(r'^[a-zA-Z0-9\s\-_àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+$', v):
            raise ValueError('Tên chứa ký tự không hợp lệ')
        return v


class VerifyOTPRequest(BaseModel):
    email: str
    otp: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    email: str


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _generate_otp() -> str:
    return str(secrets.randbelow(1000000)).zfill(6)


def _create_token(user_id: str, email: str, token_type: str = "access") -> str:
    """Tạo JWT token (access hoặc refresh)."""
    now = datetime.now(timezone.utc)
    if token_type == "refresh":
        expire = now + timedelta(minutes=REFRESH_TOKEN_EXPIRE)
        payload_type = "refresh"
    else:
        expire = now + timedelta(minutes=TOKEN_EXPIRE)
        payload_type = "access"
    
    payload = {
        "sub": user_id,
        "email": email,
        "type": payload_type,
        "exp": expire,
        "iat": now,
        "jti": secrets.token_hex(8)  # JWT ID for token revocation
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _verify_token(token: str) -> dict:
    """Xác minh JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token hết hạn")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")


def _check_rate_limit(tools, email: str, action: str) -> bool:
    """Kiểm tra rate limit cho login attempts."""
    # Skip rate limiting in dev mode
    if DEV_MODE:
        return False
    
    # Lấy số attempts trong 15 phút gần đây
    attempts = tools.db.execute(
        f"""SELECT COUNT(*) as cnt FROM failed_attempts 
           WHERE email = ? AND action = ? AND attempted_at > datetime('now', '-{ATTEMPT_WINDOW} minutes')""",
        (email, action),
        fetchall=False
    )
    
    return attempts and attempts.get("cnt", 0) >= MAX_LOGIN_ATTEMPTS


def _record_failed_attempt(tools, email: str, action: str):
    """Ghi lại failed attempt."""
    try:
        tools.db.execute_write(
            """INSERT INTO failed_attempts (email, action, attempted_at) 
               VALUES (?, ?, datetime('now'))""",
            (email, action)
        )
    except Exception as e:
        logger.warning(f"Failed to record attempt: {e}")


def _send_otp_email(email: str, otp: str) -> bool:
    """Gửi OTP qua email. Return True nếu thành công."""
    if not EMAIL_ENABLED:
        logger.warning("Email not configured. Using console logging instead.")
        print(f"\n🔐 OTP cho {email}: {otp}\n")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Mã OTP xác minh tài khoản - Trợ lý Tư vấn Học tập"
        msg["From"] = EMAIL_USER
        msg["To"] = email
        
        # HTML content
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 500px; margin: 0 auto;">
              <h2>Xác minh tài khoản của bạn</h2>
              <p>Bạn đã yêu cầu mã OTP để xác minh tài khoản tại Trợ lý Tư vấn Học tập.</p>
              <div style="background: #f0f0f0; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                <p style="margin: 0; font-size: 12px; color: #666;">Mã xác minh của bạn</p>
                <p style="margin: 10px 0; font-size: 32px; font-weight: bold; letter-spacing: 2px; color: #1a3a3a;">
                  {otp}
                </p>
              </div>
              <p style="font-size: 14px; color: #666;">
                Mã này sẽ hết hạn trong <strong>15 phút</strong>. Đừng chia sẻ mã này cho bất kỳ ai.
              </p>
              <p style="margin-top: 30px; font-size: 12px; color: #999;">
                Nếu bạn không yêu cầu mã này, vui lòng bỏ qua email này.
              </p>
            </div>
          </body>
        </html>
        """
        
        part = MIMEText(html, "html")
        msg.attach(part)
        
        # Send
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, email, msg.as_string())
        
        logger.info(f"✉️ OTP email sent to {email}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send OTP email: {e}")
        # Fallback to console
        print(f"\n🔐 OTP cho {email}: {otp}\n")
        return False


@router.post("/register-request")
def register_request(req: RegisterRequest, tools=Depends(get_academic_tools)):
    """Gửi OTP để đăng ký."""
    try:
        email = req.email.lower()
        
        # Check rate limit
        if _check_rate_limit(tools, email, "register"):
            logger.warning(f"⚠️ Rate limit exceeded for registration: {email}")
            raise HTTPException(status_code=429, detail="Quá nhiều yêu cầu. Vui lòng thử lại sau 15 phút")
        
        # Check existing user
        if tools.db.execute("SELECT 1 FROM Users WHERE email = ?", (email,), fetchall=False):
            _record_failed_attempt(tools, email, "register")
            raise HTTPException(status_code=409, detail="Email đã được đăng ký")
        
        # Check pending
        if tools.db.execute(
            "SELECT 1 FROM pending_registrations WHERE email = ? AND expires_at > datetime('now')",
            (email,), fetchall=False
        ):
            raise HTTPException(status_code=429, detail="OTP đã gửi. Vui lòng kiểm tra email")
        
        # Generate & save OTP
        otp = _generate_otp()
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE)).isoformat()
        
        tools.db.execute_write(
            """INSERT INTO pending_registrations 
               (display_name, email, password_hash, otp_hash, attempts, expires_at, created_at) 
               VALUES (?, ?, ?, ?, 0, ?, datetime('now'))""",
            (req.display_name, email, _hash(req.password), _hash(otp), expires_at)
        )
        
        logger.info(f"📧 Registration request: {email}")
        _send_otp_email(email, otp)
        
        return {
            "message": f"OTP đã gửi đến {email}. Hết hạn trong 15 phút.",
            "expires_in_seconds": 900,
            "email": email
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Lỗi đăng ký. Vui lòng thử lại")


@router.post("/verify-otp")
def verify_otp(req: VerifyOTPRequest, tools=Depends(get_academic_tools)):
    """Xác minh OTP và tạo tài khoản."""
    try:
        email = req.email.lower()
        
        # Check rate limit
        if _check_rate_limit(tools, email, "otp_verify"):
            logger.warning(f"⚠️ OTP rate limit: {email}")
            raise HTTPException(status_code=429, detail="Quá nhiều lần nhập sai. Hãy yêu cầu OTP mới")
        
        pending = tools.db.execute(
            """SELECT * FROM pending_registrations 
               WHERE email = ? AND expires_at > datetime('now')
               ORDER BY created_at DESC LIMIT 1""",
            (email,), fetchall=False
        )
        
        if not pending:
            raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu đăng ký. Hãy đăng ký lại")
        
        # Verify OTP
        if _hash(req.otp) != pending["otp_hash"]:
            attempts = pending.get("attempts", 0) + 1
            tools.db.execute_write(
                "UPDATE pending_registrations SET attempts = ? WHERE email = ?", 
                (attempts, email)
            )
            _record_failed_attempt(tools, email, "otp_verify")
            
            if attempts >= 3:
                tools.db.execute_write("DELETE FROM pending_registrations WHERE email = ?", (email,))
                logger.warning(f"⚠️ OTP attempts exceeded: {email}")
                raise HTTPException(status_code=429, detail="Nhập sai quá nhiều lần. Hãy đăng ký lại")
            
            raise HTTPException(status_code=401, detail=f"OTP không đúng ({3-attempts} lần thử còn lại)")
        
        # Create user
        tools.db.execute_write(
            """INSERT INTO Users 
               (user_id, email, password_hash, is_active, created_at, last_login) 
               VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))""",
            (email, email, pending["password_hash"])
        )
        
        # Create student record linked to user
        tools.db.execute_write(
            """INSERT INTO Students 
               (student_id, full_name, user_id) 
               VALUES (?, ?, ?)""",
            (email, pending["display_name"], email)
        )
        
        tools.db.execute_write("DELETE FROM pending_registrations WHERE email = ?", (email,))
        
        access_token = _create_token(email, email, "access")
        refresh_token = _create_token(email, email, "refresh")
        
        logger.info(f"✅ User registered: {email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": email,
            "email": email
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"OTP verification error: {e}")
        raise HTTPException(status_code=500, detail="Lỗi xác minh. Vui lòng thử lại")


@router.post("/login")
def login(req: LoginRequest, tools=Depends(get_academic_tools)):
    """Đăng nhập với email và mật khẩu."""
    try:
        email = req.email.lower()
        
        # Check rate limit
        if _check_rate_limit(tools, email, "login"):
            logger.warning(f"⚠️ Login rate limit: {email}")
            raise HTTPException(status_code=429, detail="Quá nhiều lần đăng nhập thất bại. Hãy thử lại sau 15 phút")
        
        user = tools.db.execute("SELECT * FROM Users WHERE email = ?", (email,), fetchall=False)
        
        if not user or _hash(req.password) != user["password_hash"]:
            _record_failed_attempt(tools, email, "login")
            logger.warning(f"⚠️ Failed login attempt: {email}")
            raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
        
        if not user.get("is_active", False):
            raise HTTPException(status_code=403, detail="Tài khoản bị vô hiệu hóa")
        
        # Update last login
        tools.db.execute_write(
            "UPDATE Users SET last_login = datetime('now') WHERE user_id = ?", 
            (user["user_id"],)
        )
        
        # Create tokens
        access_token = _create_token(user["user_id"], user["email"], "access")
        refresh_token = _create_token(user["user_id"], user["email"], "refresh")
        
        logger.info(f"✅ User logged in: {email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user["user_id"],
            "email": user["email"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Lỗi đăng nhập. Vui lòng thử lại")


@router.post("/refresh")
def refresh_token(authorization: str = Header(None), tools=Depends(get_academic_tools)):
    """Làm mới access token bằng refresh token."""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Token không hợp lệ")
        
        token = authorization.split(" ")[1]
        payload = _verify_token(token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Không phải refresh token")
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        # Verify user still exists and is active
        user = tools.db.execute("SELECT * FROM Users WHERE user_id = ? AND is_active = 1", (user_id,), fetchall=False)
        if not user:
            raise HTTPException(status_code=401, detail="Người dùng không tồn tại")
        
        # Generate new access token
        new_access_token = _create_token(user_id, email, "access")
        
        logger.info(f"🔄 Token refreshed: {user_id}")
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Lỗi làm mới token")


@router.get("/me")
def get_current_user(authorization: str = Header(None), tools=Depends(get_academic_tools)):
    """Lấy thông tin người dùng hiện tại."""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Chưa xác thực")
        
        token = authorization.split(" ")[1]
        payload = _verify_token(token)
        
        user_id = payload.get("sub")
        user = tools.db.execute(
            "SELECT user_id, email, display_name, is_active, created_at FROM Users WHERE user_id = ?",
            (user_id,), fetchall=False
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="Người dùng không tồn tại")
        
        return {
            "user_id": user["user_id"],
            "email": user["email"],
            "display_name": user.get("display_name", ""),
            "is_active": user["is_active"],
            "created_at": user["created_at"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Get user error: {e}")
        raise HTTPException(status_code=401, detail="Chưa xác thực")
