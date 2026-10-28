"""
Gemini Integration — ใช้ Google Pro ให้คุ้มค่า
ช่วยค้นหาสคริปต์ให้ครอบคลุมแม้แมพที่คนแทบไม่เล่น
"""
import os, json, asyncio, aiohttp

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"


class GeminiSearchHelper:
    """ใช้ Gemini ขยายการค้นหาสคริปต์ Roblox"""

    def __init__(self):
        self.session = None

    async def _get_session(self):
        import aiohttp
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        import aiohttp
        if self.session and not self.session.closed:
            await self.session.close()

    async def expand_query(self, query: str) -> dict:
        """
        ใช้ Gemini ขยายการค้นหา:
        - ระบุชื่อเกมจริง (แม้พิมพ์ผิด/ไม่ครบ)
        - สร้างคำค้นหาทางเลือก
        - แนะนำประเภทสคริปต์ที่เหมาะสม
        """
        prompt = f"""ผู้ใช้กำลังค้นหาสคริปต์ Roblox ด้วยคำว่า: "{query}"

ตอบเป็น JSON เท่านั้น (ไม่ต้องอธิบายเพิ่ม):
{{
  "game_name": "ชื่อเกม Roblox ที่แท้จริง (หรือ 'unknown')",
  "alt_searches": ["คำค้นหาทางเลือก 3-5 รายการ"],
  "suggested_script_types": ["farm", "admin", "esp", "mod", "tool", "aimbot"],
  "is_roblox_game": true/false,
  "recommended_for_obscure": true/false,
  "search_description": "คำอธิบายสั้น ๆ ว่าควรค้นหาอะไร"
}}

เกม Roblox ยอดนิยมน้อยที่อาจเจอ: "Natural Disaster Survival", "Tower Defense Simulator", "Anime Fighters Simulator", "Fisch", "Anime Vanguards", "Grand Piece Online", "Project Slayers", "A Piece", "King Legacy", "Blox Fruits", "Blox Legend"

ตอบเป็นภาษาไทยสั้น ๆ กระชับ แต่ JSON ต้องถูกต้อง 100%"""

        try:
            sess = await self._get_session()
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 512,
                    "responseMimeType": "application/json"
                }
            }
            async with sess.post(GEMINI_ENDPOINT, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                data = await resp.json()
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    result = json.loads(text)
                    return result
                except (KeyError, IndexError, json.JSONDecodeError) as e:
                    # ถ้า Gemini ไม่ตอบเป็น JSON ถูก ให้สร้าง fallback
                    return {
                        "game_name": query,
                        "alt_searches": [query, query.lower(), f"{query} farm", f"{query} script"],
                        "suggested_script_types": ["farm", "mod"],
                        "is_roblox_game": True,
                        "recommended_for_obscure": False,
                        "search_description": f"ค้นหาสคริปต์ Roblox สำหรับ {query}"
                    }
        except Exception:
            return {
                "game_name": query,
                "alt_searches": [query],
                "suggested_script_types": ["script"],
                "is_roblox_game": False,
                "recommended_for_obscure": False,
                "search_description": f"ค้นหาสคริปต์สำหรับ {query}"
            }


# Global instance
gemini = GeminiSearchHelper()
