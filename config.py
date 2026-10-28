import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
DEFAULT_COOLDOWN = int(os.getenv("DEFAULT_COOLDOWN_SECONDS", "7"))
API_PORT = int(os.getenv("API_PORT", "49288"))

# Styling & Colors
COLOR_PRIMARY = 0x8A2BE2
COLOR_SUCCESS = 0x00FF7F
COLOR_ERROR = 0xFF3860
COLOR_INFO = 0x00D1B2
COLOR_WARNING = 0xFFDD57

# Bypass API Endpoints — ZERO external third-party APIs (Strict Self-Hosted Engine)
BYPASS_ENDPOINTS = []

# ─────────────────────────────────────────────────────────────
# Dynamic Token Configuration (Platoboost / Delta)
# ─────────────────────────────────────────────────────────────
PLATOBOOST_TOKEN = os.getenv("PLATOBOOST_TOKEN", "297h")
PLATOBOOST_COOKIE_NAME = "TK_INCLUDE"
PLATOBOOST_COOKIE_VALUE = "1"

# RTaO Primary API Configuration (Priority #1 Engine)
RTAO_API_KEY = os.getenv("RTAO_API_KEY", "rtao-864d7419ae7d506c")
RTAO_API_BASE = "https://api.rtaoexe.xyz"
RTAO_API_BYPASS_ENDPOINT = "https://api.rtaoexe.xyz/bypass"
RTAO_API_SUPPORTED_ENDPOINT = "https://api.rtaoexe.xyz/supported"


# ─────────────────────────────────────────────────────────────
# Provider catalog — merged from Evo-Bypass catalog.js (Phase 1D)
# Key System providers, Ad-links, Social unlock, File hosts
# ─────────────────────────────────────────────────────────────
PROVIDERS = {

    # ── Key Systems (Executors) ──────────────────────────────
    "delta": {
        "name": "Delta Executor",
        "emoji": "🔺",
        "patterns": ["gateway.platoboost.com/a/2", "deltaexecutor.co", "delta.co"],
        "color": 0xFF4500,
        "category": "Key System"
    },
    "luarmor": {
        "name": "Luarmor",
        "emoji": "🛡️",
        "patterns": ["ads.luarmor.net", "luarmor.net"],
        "color": 0x7289DA,
        "category": "Key System"
    },
    "platoboost": {
        "name": "Platoboost",
        "emoji": "🪐",
        "patterns": ["platoboost.com", "platoboost.net", "gateway.platoboost.com", "platorelay.com"],
        "color": 0x1ABC9C,
        "category": "Key System"
    },
    "trigon": {
        "name": "Trigon Evo",
        "emoji": "⭕",
        "patterns": ["trigonevo.com", "trigon.gg"],
        "color": 0x6C2BD9,
        "category": "Key System"
    },
    "hydrogen": {
        "name": "Hydrogen",
        "emoji": "⚗️",
        "patterns": ["hydrogen.lat"],
        "color": 0x00BCD4,
        "category": "Key System"
    },
    "codex": {
        "name": "Codex",
        "emoji": "📜",
        "patterns": ["codex.lol"],
        "color": 0x795548,
        "category": "Key System"
    },
    "violated": {
        "name": "Violated",
        "emoji": "💀",
        "patterns": ["violated.lol"],
        "color": 0xD32F2F,
        "category": "Key System"
    },
    "bloxscript": {
        "name": "Blox Script",
        "emoji": "🟦",
        "patterns": ["blox-script.com", "boblox-script.com"],
        "color": 0x1565C0,
        "category": "Key System"
    },
    "pandadev": {
        "name": "Panda Development",
        "emoji": "🐼",
        "patterns": ["pandadevelopment.net"],
        "color": 0x4CAF50,
        "category": "Key System"
    },

    # ── Ad-link Shorteners ────────────────────────────────────
    "linkvertise": {
        "name": "Linkvertise",
        "emoji": "⚡",
        "patterns": ["linkvertise.com", "linkvertise.net", "link-to.net", "direct-link.net", "file-link.net", "link-hub.net"],
        "color": 0xFF6B00,
        "category": "Ad-link"
    },
    "lootlabs": {
        "name": "LootLabs",
        "emoji": "💎",
        "patterns": [
            "loot-links.com", "lootlinks.co", "loot-labs.com", "lootlabs.gg",
            "lootlabs.cl", "lootdest.org", "lootdest.info", "lootdest.com",
            "loot-reward.com", "links.lootlabs.gg"
        ],
        "color": 0x9B59B6,
        "category": "Ad-link"
    },
    "workink": {
        "name": "Work.ink",
        "emoji": "💼",
        "patterns": ["work.ink", "workink.net", "r.work.ink"],
        "color": 0x3498DB,
        "category": "Ad-link"
    },
    "admaven": {
        "name": "Ad-Maven",
        "emoji": "📢",
        "patterns": ["ad-maven.com", "admaven.com"],
        "color": 0xFF9800,
        "category": "Ad-link"
    },
    "lockr": {
        "name": "Lockr",
        "emoji": "🔒",
        "patterns": ["lockr.com", "lockr.so", "lockr.net", "unlockr.ca"],
        "color": 0xE74C3C,
        "category": "Ad-link"
    },
    "shrtfly": {
        "name": "Shrtfly",
        "emoji": "✈️",
        "patterns": ["shrtfly.com", "shortfly.co", "stfly.vip"],
        "color": 0x009688,
        "category": "Ad-link"
    },
    "boostink": {
        "name": "Boost.ink",
        "emoji": "🚀",
        "patterns": ["boost.ink", "bst.sh"],
        "color": 0xF1C40F,
        "category": "Ad-link"
    },
    "gplinks": {
        "name": "GPlinks",
        "emoji": "🔗",
        "patterns": ["gplinks.co", "gplinks.in", "gplinks.me"],
        "color": 0x607D8B,
        "category": "Ad-link"
    },
    "ouo": {
        "name": "Ouo.io",
        "emoji": "🌀",
        "patterns": ["ouo.io", "ouo.press"],
        "color": 0x00ACC1,
        "category": "Ad-link"
    },
    "shrinkme": {
        "name": "Shrinkme",
        "emoji": "📉",
        "patterns": ["shrinkme.io", "shrink.pe", "shrinkearn.com", "shrinkurl.org"],
        "color": 0x558B2F,
        "category": "Ad-link"
    },
    "clksh": {
        "name": "Clk.sh",
        "emoji": "⏱️",
        "patterns": ["clk.sh", "cuty.io", "exe.io"],
        "color": 0x4527A0,
        "category": "Ad-link"
    },
    "linkunlocker": {
        "name": "LinkUnlocker",
        "emoji": "🔑",
        "patterns": ["linkunlocker.com", "link-unlock.com", "arolinks.com"],
        "color": 0x37474F,
        "category": "Ad-link"
    },

    # ── Social Unlock ─────────────────────────────────────────
    "rekonise": {
        "name": "Rekonise",
        "emoji": "🔓",
        "patterns": ["rekonise.com", "rekonise.org", "rkns.link"],
        "color": 0x2ECC71,
        "category": "Social Unlock"
    },
    "sub2unlock": {
        "name": "Sub2Unlock",
        "emoji": "▶️",
        "patterns": ["sub2unlock.com", "sub2unlock.net", "sub2unlock.io", "sub2unlock.me"],
        "color": 0xFF0000,
        "category": "Social Unlock"
    },
    "sub4unlock": {
        "name": "Sub4Unlock",
        "emoji": "🔔",
        "patterns": ["sub4unlock.com", "sub4unlock.me"],
        "color": 0xE53935,
        "category": "Social Unlock"
    },
    "mboost": {
        "name": "mBoost",
        "emoji": "📱",
        "patterns": ["mboost.me"],
        "color": 0x039BE5,
        "category": "Social Unlock"
    },
    "socialwolvez": {
        "name": "SocialWolvez",
        "emoji": "🐺",
        "patterns": ["socialwolvez.com", "social-unlock.com", "link4sub.com"],
        "color": 0x5C6BC0,
        "category": "Social Unlock"
    },

    # ── File Hosts ────────────────────────────────────────────
    "mediafire": {
        "name": "MediaFire",
        "emoji": "📁",
        "patterns": ["mediafire.com"],
        "color": 0x1565C0,
        "category": "File Host"
    },
    "rapidgator": {
        "name": "Rapidgator",
        "emoji": "💾",
        "patterns": ["rapidgator.net"],
        "color": 0xBF360C,
        "category": "File Host"
    },
    "turbobit": {
        "name": "Turbobit",
        "emoji": "⚡",
        "patterns": ["turbobit.net"],
        "color": 0xF57F17,
        "category": "File Host"
    },
    "krakenfiles": {
        "name": "KrakenFiles",
        "emoji": "🐙",
        "patterns": ["krakenfiles.com"],
        "color": 0x00E676,
        "category": "File Host"
    },
    "gofile": {
        "name": "GoFile",
        "emoji": "📂",
        "patterns": ["gofile.io"],
        "color": 0x2979FF,
        "category": "File Host"
    },
    "pixeldrain": {
        "name": "PixelDrain",
        "emoji": "👾",
        "patterns": ["pixeldrain.com"],
        "color": 0x651FFF,
        "category": "File Host"
    },
    "adfly": {
        "name": "AdFly Network",
        "emoji": "🪰",
        "patterns": [
            "adf.ly", "j.gs", "q.gs", "ay.gy", "zo.ee", "microify.com",
            "tinyium.com", "atominik.com", "bluenik.com", "bitigee.com"
        ],
        "color": 0xFFC107,
        "category": "Ad-link"
    },
    "adlinkfly": {
        "name": "AdLinkFly Network",
        "emoji": "⚡",
        "patterns": [
            "droplink.co", "tnlink.in", "rocklinks.net", "try2link.com",
            "tekcrypt.in", "short2url.in", "moneykamalo.com", "easysky.in",
            "indianshortner.in", "crazyblog.in", "tnvalue.in", "shortingly.me",
            "dulink.in", "bindaaslinks.com", "pdiskshortener.com", "mdiskshortner.link",
            "earnl.xyz", "rewayatcafe.com", "bitshorten.com", "rocklink.in",
            "ez4short.com", "xpshort.com", "vearnl.in", "adrinolinks.in",
            "techymozo.com", "linkbnao.com", "linksxyz.in", "short-jambo.com",
            "linkpays.in", "pi-l.ink", "earn4link.in", "open2get.in"
        ],
        "color": 0x00B0FF,
        "category": "Ad-link"
    },

    # ── Fallback ──────────────────────────────────────────────
    "general": {
        "name": "Shortened Link",
        "emoji": "🔗",
        "patterns": [],
        "color": COLOR_PRIMARY,
        "category": "General"
    }
}

# Flat domain list for quick lookup (used by API server)
ALL_SUPPORTED_DOMAINS = []
for k, v in PROVIDERS.items():
    if k != "general":
        for p in v["patterns"]:
            ALL_SUPPORTED_DOMAINS.append({
                "name": v["name"],
                "domain": p,
                "category": v.get("category", "General"),
                "status": "active",
                "emoji": v["emoji"]
            })
