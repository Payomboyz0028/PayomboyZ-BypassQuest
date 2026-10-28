# ⚡ KeyBypass Discord Bot (Python Edition)

ระบบบอท Discord สำหรับการบายพาสลิงก์โฆษณาอัตโนมัติ (**Auto Link Bypasser**) รองรับบริการย่อยมากมาย เช่น **Linkvertise, LootLabs/LootLinks, Work.ink, Rekonise, Lockr, Boost.ink, Platoboost ฯลฯ**

---

## ✨ คุณสมบัติเด่น (Features)

1. 🔍 **Auto Domain Detection**: ตรวจจับโดเมนและประเภทผู้ให้บริการลิงก์อัตโนมัติ พร้อมไอคอนและสีประจำแบรนด์
2. ⏱️ **Cooldown / Anti-Spam System**: ป้องกันการสแปมคำสั่งโดยกำหนด Cooldown ต่อผู้ใช้พร้อมหน้าจอแจ้งเตือนนับถอยหลัง
3. 📊 **Bypass Statistics (`/stats`)**: ระบบบันทึกสถิติการใช้งาน real-time ทั้งจำนวนที่บายพาสสำเร็จ, ผู้ใช้งานแยกตามเซิร์ฟเวอร์, และจัดอันดับผู้ให้บริการยอดนิยม (เก็บบันทึกลงไฟล์ JSON อัตโนมัติ)
4. 📩 **DM Support & Ephemeral Modes**: มีตัวเลือกส่งลิงก์ตรงปลายทางเข้าทาง **Message (DM)** ส่วนตัว หรือกดปุ่มสั่งส่งเข้า DM ใน Embed
5. 🎨 **Cyberpunk / Glassmorphic Embeds**: หน้าตา Embed สวยงามสไตล์ Glassmorphism พร้อม **UI Buttons** (`Open Direct Link`, `Send to DM`, `Copy Link`)

---

## 📁 โครงสร้างโปรเจกต์ (Project Structure)

```text
discord_bot/
├── .env                  # ไฟล์ตั้งค่า Token และ API (ใส่ DISCORD_BOT_TOKEN ที่นี่)
├── .env.example          # ตัวอย่างไฟล์ตั้งค่า
├── config.py             # ค่า Configuration และพาเลตสี / ไอคอน
├── requirements.txt      # รายการ Library ของ Python (discord.py, aiohttp ฯลฯ)
├── main.py               # จุดเริ่มต้นเปิดทำงานบอท (Main Entry Point)
├── utils/
│   ├── bypasser.py       # ระบบตรวจจับโดเมนและ Client เชื่อมต่อ KeyBypass API
│   ├── embeds.py         # ตัวสร้าง Discord Embeds & UI Buttons (Open, Copy, DM)
│   └── stats_manager.py  # ระบบบันทึกและคำนวณสถิติ persistent JSON
└── cogs/
    ├── bypass.py         # คำสั่ง Slash Command: /bypass
    └── stats.py          # คำสั่ง Slash Command: /stats
```

---

## 🚀 วิธีติดตั้งและเปิดใช้งาน (Setup & Run)

### 1. ติดตั้ง Library ที่จำเป็น
เปิด Terminal / Command Prompt แล้วรันคำสั่ง:
```bash
pip install -r requirements.txt
```

### 2. ตั้งค่า Discord Bot Token
1. เปิดไฟล์ `discord_bot/.env`
2. นำ **Bot Token** จาก [Discord Developer Portal](https://discord.com/developers/applications) มาใส่ในช่อง `DISCORD_BOT_TOKEN`:
   ```env
   DISCORD_BOT_TOKEN=ใส่_TOKEN_บอทของคุณที่นี่
   ```

> 💡 **หมายเหตุ**: อย่าลืมเปิด **MESSAGE CONTENT INTENT** ในหน้า Discord Developer Portal -> Bot -> Privileged Gateway Intents

### 3. เริ่มรันบอท
```bash
python main.py
```

---

## 💬 การใช้งานคำสั่งใน Discord

| คำสั่ง (Slash Command) | คำอธิบาย |
| :--- | :--- |
| `/bypass url:<link> [send_dm:True/False]` | ปลดล็อกและบายพาสลิงก์โฆษณา รับลิงก์ตรงปลายทางพร้อมปุ่มกด |
| `/stats` | ดูแผงสถิติรวมของระบบ และสถิติของเซิร์ฟเวอร์ปัจจุบัน |
