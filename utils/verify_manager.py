"""
Verification Challenge Manager for PAYOMBØYZ Verification.
Tracks active ephemeral captcha challenges, TTL, attempts, and verification state.
"""
import time
from typing import Optional, Tuple
from utils.captcha_generator import generate_captcha
from utils.config_manager import guild_config

class VerifyManager:
    """In-memory active challenge session store with automatic 5-minute TTL."""
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        # user_id -> { "code": str, "role_id": int, "guild_id": int, "expires_at": float, "attempts": int }
        self._sessions: dict[int, dict] = {}
        
    def cleanup_expired(self):
        now = time.time()
        expired = [uid for uid, s in self._sessions.items() if s["expires_at"] <= now]
        for uid in expired:
            self._sessions.pop(uid, None)
            
    def create_challenge(self, user_id: int, guild_id: int, role_id: int) -> Tuple[str, bytes]:
        """Generate a new captcha challenge and store session."""
        self.cleanup_expired()
        code, png_bytes = generate_captcha(length=5)
        self._sessions[user_id] = {
            "code": code.upper().strip(),
            "role_id": role_id,
            "guild_id": guild_id,
            "expires_at": time.time() + self.ttl,
            "attempts": 0
        }
        return code, png_bytes
        
    def get_challenge(self, user_id: int) -> Optional[dict]:
        """Retrieve active challenge if not expired."""
        self.cleanup_expired()
        session = self._sessions.get(user_id)
        if not session:
            return None
        if session["expires_at"] <= time.time():
            self._sessions.pop(user_id, None)
            return None
        return session
        
    def verify_answer(self, user_id: int, user_input: str) -> Tuple[bool, str, Optional[int]]:
        """
        Verify submitted answer against active session.
        Returns:
            (is_valid, message, role_id)
        """
        session = self.get_challenge(user_id)
        if not session:
            return False, "⚠️ เซสชันการยืนยันตัวตนหมดอายุแล้ว (เกิน 5 นาที) โปรดกดปุ่ม \"ยืนยันตัวตน\" ใหม่อีกครั้ง", None
            
        clean_input = user_input.strip().upper()
        expected = session["code"]
        role_id = session["role_id"]
        
        session["attempts"] += 1
        
        if clean_input == expected:
            # Successfully solved
            self._sessions.pop(user_id, None)
            return True, "Success", role_id
            
        if session["attempts"] >= 3:
            self._sessions.pop(user_id, None)
            return False, "❌ คุณตอบผิดเกิน 3 ครั้ง เซสชันนี้ถูกยกเลิกแล้ว โปรดกดปุ่ม \"ยืนยันตัวตน\" เพื่อขอรับ Captcha ใหม่", None
            
        return False, f"❌ รหัส Captcha ไม่ถูกต้อง (ลองได้อีก {3 - session['attempts']} ครั้ง)", role_id

# Global instance
verify_manager = VerifyManager(ttl_seconds=300)
