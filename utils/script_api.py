"""
External Script APIs — Integration for ScriptBlox and Rscripts
ดึงข้อมูลสคริปต์จาก API ภายนอกเพื่อเพิ่มฐานข้อมูลให้ครอบคลุม
"""
import asyncio
import aiohttp
import os
from typing import Optional

# ScriptBlox API
SCRIPTBLOX_BASE = "https://scriptblox.com/api/script"
SCRIPTBLOX_SEARCH = f"{SCRIPTBLOX_BASE}/search"

# Rscripts API
RSCRIPTS_API = "https://api.rscripts.net"
RSCRIPTS_SEARCH = f"{RSCRIPTS_API}/v1/search"
RSCRIPTS_SCRIPTS = f"{RSCRIPTS_API}/v1/scripts"


class ScriptAPIError(Exception):
    """Error เกิดขึ้นเมื่อเรียก API สคริปต์"""
    pass


class ScriptAPIClient:
    """Client สำหรับเรียก API สคริปต์"""

    def __init__(self, rscripts_key: str = None):
        self.session: Optional[aiohttp.ClientSession] = None
        self.rscripts_key = rscripts_key or "rsc_live_yAW8b59q_nR3Z8p1-vCB1MC4Zhkg2LTB"
        self._headers_scriptblox = {
            "User-Agent": "Mozilla/5.0 (compatible; KeyBypassBot/1.0)"
        }
        self._headers_rscripts = {
            "Authorization": f"Bearer {self.rscripts_key}" if self.rscripts_key else "Bearer rsc_default",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; KeyBypassBot/1.0)"
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    # ── ScriptBlox ───────────────────────────────────────────
    async def search_scriptblox(self, query: str, limit: int = 10, page: int = 1) -> list[dict]:
        """ค้นหาสคริปต์จาก ScriptBlox.com"""
        try:
            session = await self._get_session()
            params = {
                "q": query,
                "max": min(limit, 20),
                "page": page
            }

            async with session.get(
                SCRIPTBLOX_SEARCH,
                params=params,
                headers=self._headers_scriptblox,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    if "<html" in text.lower() or "doctype" in text.lower():
                        text = f"HTTP {resp.status}"
                    raise ScriptAPIError(f"ScriptBlox API error: {resp.status} - {text[:200]}")

                data = await resp.json()
                result = data.get("result", {})
                scripts = result.get("scripts", [])

                return [self._normalize_scriptblox(s) for s in scripts]

        except aiohttp.ClientError as e:
            raise ScriptAPIError(f"ScriptBlox connection error: {e}")
        except Exception as e:
            raise ScriptAPIError(f"ScriptBlox error: {e}")

    def _normalize_scriptblox(self, raw: dict) -> dict:
        """แปลงข้อมูล ScriptBlox ให้เป็นรูปแบบมาตรฐานในระบบ"""
        game_data = raw.get("game", {})
        game_name = game_data.get("name", "Unknown") if isinstance(game_data, dict) else (str(game_data) if game_data else "Unknown")

        # Resolving thumbnail/image
        img = raw.get("image", "")
        if not img and isinstance(game_data, dict):
            img = game_data.get("imageUrl", "") or game_data.get("thumbnailUrl", "")
        if img and img.startswith("/"):
            img = f"https://scriptblox.com{img}"

        slug = raw.get("slug", "")
        return {
            "id": raw.get("_id"),
            "name": raw.get("title", "Unknown"),
            "game": game_name,
            "game_data": game_data,
            "type": raw.get("scriptType", "unknown").lower(),
            "description": raw.get("description", "")[:300],
            "url": f"https://scriptblox.com/script/{slug}" if slug else "",
            "raw_url": raw.get("script", ""),  # Contains loadstring or lua code
            "executor": "krnl, synapse, fluxus, delta, hydrogen, arceus",
            "verified": raw.get("verified", False),
            "views": raw.get("views", 0),
            "has_key": raw.get("key", False),
            "is_universal": raw.get("isUniversal", False),
            "source": "scriptblox_api",
            "domain": "scriptblox.com",
            "image": img,
            "created": str(raw.get("createdAt", ""))[:10] if raw.get("createdAt") else "",
            "updated": str(raw.get("lastBump", raw.get("updatedAt", "")))[:10] if (raw.get("lastBump") or raw.get("updatedAt")) else ""
        }

    # ── Rscripts ───────────────────────────────────────────────
    async def search_rscripts(self, query: str, limit: int = 10, page: int = 1) -> list[dict]:
        """ค้นหาสคริปต์จาก Rscripts API"""
        try:
            session = await self._get_session()
            params = {
                "q": query,
                "index": "scripts",
                "limit": min(limit, 20),
                "page": page,
                "includeScript": "false"
            }

            async with session.get(
                RSCRIPTS_SEARCH,
                params=params,
                headers=self._headers_rscripts,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    if "<html" in text.lower() or "doctype" in text.lower():
                        text = f"HTTP {resp.status} (Cloudflare)"
                    raise ScriptAPIError(f"Rscripts API error: {resp.status} - {text[:200]}")

                data = await resp.json()
                result = data.get("data", data.get("result", {}))
                scripts = result.get("scripts", []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
                return [self._normalize_rscripts(s) for s in scripts]

        except aiohttp.ClientError as e:
            raise ScriptAPIError(f"Rscripts connection error: {e}")
        except Exception as e:
            raise ScriptAPIError(f"Rscripts error: {e}")

    def _normalize_rscripts(self, raw: dict) -> dict:
        """แปลงข้อมูล Rscripts API (รูปแบบจริง: data.scripts)"""
        slug = raw.get("slug", "")
        if not slug and raw.get("title"):
            slug = raw.get("title","").lower().replace(" ","-").replace("'","-")[:50]
        game_obj = raw.get("game", {})
        game_name = game_obj.get("title", game_obj.get("name", "Unknown")) if isinstance(game_obj, dict) else (str(game_obj) if game_obj else "Unknown")
        
        img = raw.get("imageUrl", "")
        if not img and isinstance(game_obj, dict):
            img = game_obj.get("thumbnailUrl") or game_obj.get("logoUrl") or ""

        raw_script = raw.get("rawScript", "")
        if not raw_script and slug:
            raw_script = f"https://rscripts.net/raw/{slug}.txt"

        return {
            "id": raw.get("id"),
            "name": raw.get("title", "Unknown"),
            "game": game_name,
            "game_data": game_obj,
            "type": "auto_farm" if any(k in (raw.get("title","") or "").lower() for k in ["farm","auto","hub"]) else ("mod" if "hub" in (raw.get("title","") or "").lower() else "script"),
            "description": (raw.get("description","") or "ไม่มีรายละเอียด")[:300],
            "url": f"https://rscripts.net/script/{slug}" if slug else "",
            "raw_url": raw_script,
            "executor": "krnl, synapse, fluxus, delta, hydrogen, arceus",
            "verified": raw.get("verified", False),
            "views": raw.get("views", 0),
            "has_key": raw.get("isKeySystem", False),
            "is_universal": raw.get("isMobileReady", not raw.get("isPaid", False)),
            "source": "rscripts_api",
            "domain": "rscripts.net",
            "image": img,
            "created": str(raw.get("created", ""))[:10] if raw.get("created") else "",
            "updated": str(raw.get("updated", ""))[:10] if raw.get("updated") else "",
            "creator": raw.get("creator",{}).get("username", "Unknown") if isinstance(raw.get("creator"), dict) else "Unknown"
        }

    # ── Combined Search ───────────────────────────────────────
    async def search_all(self, query: str, limit: int = 10) -> dict:
        """ค้นหาทั้งหมดจากทุก API พร้อมกัน"""
        results = {
            "scriptblox": [],
            "rscripts": [],
            "error": []
        }

        # ค้นหาจาก 2 API พร้อมกัน
        async def fetch_scriptblox():
            try:
                return await self.search_scriptblox(query, limit=limit), None
            except Exception as e:
                return [], str(e)

        async def fetch_rscripts():
            try:
                return await self.search_rscripts(query, limit=limit), None
            except Exception as e:
                return [], str(e)

        (sb_results, sb_err), (rs_results, rs_err) = await asyncio.gather(
            fetch_scriptblox(),
            fetch_rscripts()
        )

        results["scriptblox"] = sb_results
        results["rscripts"] = rs_results

        if sb_err:
            results["error"].append(f"ScriptBlox: {sb_err}")
        if rs_err:
            results["error"].append(f"Rscripts: {rs_err}")

        return results

    async def get_trending_scriptblox(self, limit: int = 10) -> list[dict]:
        """ดึงสคริปต์ยอดนิยมจาก ScriptBlox"""
        # ScriptBlox ไม่มี endpoint trending โดยตรง ใช้ search กับ query ว่าง
        return await self.search_scriptblox("", limit=limit)

    async def get_trending_rscripts(self, limit: int = 10) -> list[dict]:
        """ดึงสคริปต์ยอดนิยมจาก Rscripts"""
        try:
            session = await self._get_session()
            url = f"{RSCRIPTS_API}/v1/trending"
            async with session.get(url, headers=self._headers_rscripts, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    raise ScriptAPIError(f"Trending API error: {resp.status}")
                data = await resp.json()
                scripts = data.get("success", [])
                return [self._normalize_rscripts_script_detail(s) for s in scripts]
        except Exception as e:
            raise ScriptAPIError(f"Trending error: {e}")

    def _normalize_rscripts_script_detail(self, raw: dict) -> dict:
        """แปลงข้อมูลจาก trending endpoint"""
        script = raw.get("script", {})
        user = raw.get("user", {})
        slug = script.get("slug", "")

        return {
            "id": script.get("_id"),
            "name": script.get("title", "Unknown"),
            "game": script.get("game", {}).get("name", "Unknown") if isinstance(script.get("game"), dict) else "Unknown",
            "type": "trending",
            "description": script.get("description", "")[:300],
            "url": f"https://rscripts.net/script/{slug}",
            "raw_url": f"https://rscripts.net/raw/script/{slug}" if slug else "",
            "executor": "krnl, synapse, fluxus",
            "views": raw.get("views", 0),
            "verified": user.get("verified", False),
            "creator": user.get("username", "Unknown"),
            "source": "rscripts_trending",
            "domain": "rscripts.net"
        }

    async def get_script_detail_rscripts(self, script_id: str) -> dict:
        """ดึงรายละเอียดสคริปต์เฉพาะจาก Rscripts"""
        try:
            session = await self._get_session()
            url = f"{RSCRIPTS_API}/v1/scripts/{script_id}"
            async with session.get(url, headers=self._headers_rscripts, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    raise ScriptAPIError(f"Script detail API error: {resp.status}")
                data = await resp.json()
                return self._normalize_rscripts(data.get("script", data))
        except Exception as e:
            raise ScriptAPIError(f"Script detail error: {e}")


# Global instance
script_api = ScriptAPIClient()


# ── Utility ─────────────────────────────────────────────────────
async def search_with_fallback(query: str) -> list[dict]:
    """ค้นหาสคริปต์พร้อมกันจากหลายแหล่ง (ScriptBlox + RScripts + Local) แบบ Fail-Safe"""
    all_results = []

    try:
        tasks = [
            script_api.search_scriptblox(query, limit=25),
            script_api.search_rscripts(query, limit=25)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                all_results.extend(res)
    except Exception:
        pass

    # Fallback to local database if external sources yielded nothing
    if not all_results:
        try:
            import json, os
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "scripts.json")
            if os.path.exists(db_path):
                with open(db_path, "r", encoding="utf-8") as f:
                    db = json.load(f)
                q_lower = query.lower()
                for cat, s_list in db.items():
                    for s in s_list:
                        if q_lower in s.get("name", "").lower() or q_lower in s.get("game", "").lower():
                            all_results.append({**s, "source": cat})
        except Exception:
            pass

    # Deduplicate by name/url
    seen = set()
    deduped = []
    for r in all_results:
        key = f"{r.get('url', '')}|{r.get('name', '')}".strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(r)

    return deduped