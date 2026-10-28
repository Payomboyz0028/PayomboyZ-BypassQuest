import json
import os
from datetime import datetime, date

STATS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "stats.json")

class StatsManager:
    """Manages persistent statistics for the Discord Bypasser Bot."""

    def __init__(self):
        self._ensure_data_dir()
        self.stats = self._load_stats()

    def _ensure_data_dir(self):
        data_dir = os.path.dirname(STATS_FILE)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

    def _load_stats(self) -> dict:
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "total_bypassed": 0,
            "today_date": str(date.today()),
            "today_count": 0,
            "providers_count": {},
            "users_count": {},
            "servers_count": {}
        }

    def save(self):
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[StatsManager] Error saving stats: {e}")

    def record_bypass(self, provider_key: str, user_id: int, guild_id: int = None):
        """Records a successful link bypass."""
        today_str = str(date.today())
        if self.stats.get("today_date") != today_str:
            self.stats["today_date"] = today_str
            self.stats["today_count"] = 0

        self.stats["total_bypassed"] = self.stats.get("total_bypassed", 0) + 1
        self.stats["today_count"] = self.stats.get("today_count", 0) + 1

        # Provider stats
        providers = self.stats.setdefault("providers_count", {})
        providers[provider_key] = providers.get(provider_key, 0) + 1

        # User stats
        str_user_id = str(user_id)
        users = self.stats.setdefault("users_count", {})
        users[str_user_id] = users.get(str_user_id, 0) + 1

        # Server stats
        if guild_id:
            str_guild_id = str(guild_id)
            servers = self.stats.setdefault("servers_count", {})
            servers[str_guild_id] = servers.get(str_guild_id, 0) + 1

        self.save()

    def get_summary(self) -> dict:
        """Returns summarized stats for dashboard/embed display."""
        today_str = str(date.today())
        today_count = self.stats.get("today_count", 0) if self.stats.get("today_date") == today_str else 0
        
        return {
            "total_bypassed": self.stats.get("total_bypassed", 0),
            "today_count": today_count,
            "unique_users": len(self.stats.get("users_count", {})),
            "unique_servers": len(self.stats.get("servers_count", {})),
            "top_providers": sorted(
                self.stats.get("providers_count", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

# Global Instance
stats_manager = StatsManager()
