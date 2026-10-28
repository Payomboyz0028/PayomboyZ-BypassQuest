"""
GuildConfigManager — Persistent per-guild configuration.
Stores panel channel ID, result/log channel ID, and other guild settings.
"""
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "guild_configs.json")

class GuildConfigManager:
    def __init__(self):
        self._ensure_dir()
        self._last_mtime = 0
        self.configs: dict = self._load()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    def _load(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                self._last_mtime = os.path.getmtime(CONFIG_FILE)
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        self._last_mtime = 0
        return {}

    def _reload_if_changed(self):
        try:
            if os.path.exists(CONFIG_FILE):
                mtime = os.path.getmtime(CONFIG_FILE)
                if getattr(self, "_last_mtime", 0) != mtime:
                    self.configs = self._load()
        except Exception:
            pass

    def _save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.configs, f, indent=2, ensure_ascii=False)
        try:
            self._last_mtime = os.path.getmtime(CONFIG_FILE)
        except Exception:
            pass

    def get(self, guild_id: int) -> dict:
        self._reload_if_changed()
        return self.configs.get(str(guild_id), {})

    def set_bypass_channel(self, guild_id: int, channel_id: int):
        cfg = self.configs.setdefault(str(guild_id), {})
        cfg["bypass_channel_id"] = channel_id
        cfg["panel_channel_id"] = channel_id
        self._save()

    def set_panel_channel(self, guild_id: int, channel_id: int):
        self.set_bypass_channel(guild_id, channel_id)

    def get_bypass_channel(self, guild_id: int) -> int | None:
        cfg = self.configs.get(str(guild_id), {})
        return cfg.get("bypass_channel_id") or cfg.get("panel_channel_id")

    def set_script_channel(self, guild_id: int, channel_id: int):
        cfg = self.configs.setdefault(str(guild_id), {})
        cfg["script_channel_id"] = channel_id
        self._save()

    def get_script_channel(self, guild_id: int) -> int | None:
        cfg = self.configs.get(str(guild_id), {})
        return cfg.get("script_channel_id") or cfg.get("panel_channel_id")

    def set_result_channel(self, guild_id: int, channel_id: int):
        cfg = self.configs.setdefault(str(guild_id), {})
        cfg["result_channel_id"] = channel_id
        cfg["bypass_log_channel_id"] = channel_id
        self._save()

    def get_result_channel(self, guild_id: int) -> int | None:
        self._reload_if_changed()
        cfg = self.configs.get(str(guild_id), {})
        res = cfg.get("result_channel_id") or cfg.get("bypass_log_channel_id")
        if not res and str(guild_id) == "1549398019970179152":
            return 1563723925119176774
        return res

    def set_verify_log_channel(self, guild_id: int, channel_id: int):
        cfg = self.configs.setdefault(str(guild_id), {})
        cfg["verify_log_channel_id"] = channel_id
        self._save()

    def get_verify_log_channel(self, guild_id: int) -> int | None:
        self._reload_if_changed()
        cfg = self.configs.get(str(guild_id), {})
        res = cfg.get("verify_log_channel_id")
        if not res and str(guild_id) == "1549398019970179152":
            return 1555390535215358073
        return res or cfg.get("result_channel_id")

    def get_panel_channel(self, guild_id: int) -> int | None:
        return self.get_bypass_channel(guild_id)

    def set_panel_message(self, guild_id: int, message_id: int):
        """Track which message is the panel so we can update it later."""
        cfg = self.configs.setdefault(str(guild_id), {})
        cfg["panel_message_id"] = message_id
        self._save()

    def get_panel_message(self, guild_id: int) -> int | None:
        return self.configs.get(str(guild_id), {}).get("panel_message_id")

    def set_mode(self, guild_id: int, mode: str):
        """Set guild operating mode: 'bypass', 'script', or 'full'"""
        cfg = self.configs.setdefault(str(guild_id), {})
        cfg["mode"] = mode
        self._save()

    def get_mode(self, guild_id: int) -> str:
        return self.configs.get(str(guild_id), {}).get("mode", "full")

    def is_bypass_enabled(self, guild_id: int | None) -> bool:
        if not guild_id:
            return True
        mode = self.get_mode(guild_id)
        return mode in ("bypass", "full")

    def is_script_enabled(self, guild_id: int | None) -> bool:
        if not guild_id:
            return True
        mode = self.get_mode(guild_id)
        return mode in ("script", "full")

    def set_verify_role(self, guild_id: int, role_id: int):
        cfg = self.configs.setdefault(str(guild_id), {})
        cfg["verify_role_id"] = role_id
        self._save()

    def get_verify_role(self, guild_id: int) -> int | None:
        cfg = self.configs.get(str(guild_id), {})
        return cfg.get("verify_role_id")

    def set_verify_channel(self, guild_id: int, channel_id: int):
        cfg = self.configs.setdefault(str(guild_id), {})
        cfg["verify_channel_id"] = channel_id
        self._save()

    def get_verify_channel(self, guild_id: int) -> int | None:
        cfg = self.configs.get(str(guild_id), {})
        return cfg.get("verify_channel_id")

    def set_verify_panel_message(self, guild_id: int, message_id: int):
        cfg = self.configs.setdefault(str(guild_id), {})
        cfg["verify_panel_message_id"] = message_id
        self._save()

    def get_verify_panel_message(self, guild_id: int) -> int | None:
        cfg = self.configs.get(str(guild_id), {})
        return cfg.get("verify_panel_message_id")

# Global singleton
guild_config = GuildConfigManager()
