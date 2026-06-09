# 🤖 Discord Auto Bump + Invite Tracker Bot

Ek powerful Discord bot jisme **Invite Tracker** aur **Full Auto Bump** features hain.

---

## ✨ Features

### 1. 📨 Invite Tracker
- Jab bhi koi naya member join kare, ek embed message send hoga jo batayega:
  - Kaun join hua
  - Kisne invite kiya (invite link se)
  - Inviter ke **total invites** kitne hain

### 2. 🚀 Full Auto Bump (Khud se!)
- Bot **khud se** har **2 ghante** mein Disboard `/bump` trigger karta hai
- Kisi ko kuch type karne ki zarurat **nahi** — bot sab khud karta hai
- Agar **text-based bump commands** bhi hain server mein (jaise `!d bump`, `b!bump`), unhe bhi bot khud bhejta hai
- Startup par bhi ek baar bump run hota hai
- **Smart cooldown** — sirf tab bump karta hai jab 2 ghante poore ho jayein

### 3. 🛠️ Commands
| Command | Kya karta hai |
|---------|---------------|
| `!invites [@user]` | Kisi member ke total invites dekho |
| `!bumpstatus` | Dekho kaunsa bump ready hai aur kaunsa cooldown mein hai |
| `!forcebump` | Admin ke liye — abhi turant saare bumps run karo |

---

## 🚀 Setup Guide

### Step 1: Discord Bot Banana
1. [Discord Developer Portal](https://discord.com/developers/applications) par jao
2. **New Application** → **Bot** → **Add Bot**
3. **Token** copy karo
4. Neeche **Privileged Gateway Intents** mein ye teen enable karo:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent

### Step 2: Bot ko Server mein Add Karo
Ye link use karo (apna CLIENT_ID daalo):
```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot
```

> ⚠️ `permissions=8` = Administrator. Kam permissions mein invite tracking kaam nahi karti.

### Step 3: Environment Variables Set Karo
`.env.example` copy karke `.env` banao:
```bash
cp .env.example .env
```

Phir apni values daalo:
```env
DISCORD_TOKEN=your_bot_token_here
INVITE_CHANNEL_ID=invite_log_channel_ka_id
BUMP_CHANNEL_ID=bump_channel_ka_id
DISBOARD_AUTO_BUMP=true
BUMP_TEXT_COMMANDS=!d bump,b!bump
```

> **Channel ID kaise milega?**
> Discord Settings → Advanced → **Developer Mode ON** karo
> Phir kisi bhi channel par right-click → **Copy ID**

---

## ☁️ Render Par Deploy Karna (24/7 Free)

1. [render.com](https://render.com) par account banao
2. **New → Web Service** click karo
3. Is GitHub repo ko connect karo: `Ayush7hx/discord-invite-bump-bot`
4. Ye settings karo:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Instance Type:** Free
5. **Environment Variables** mein ye add karo:

| Key | Value |
|-----|-------|
| `DISCORD_TOKEN` | Apna bot token |
| `INVITE_CHANNEL_ID` | Invite log channel ID |
| `BUMP_CHANNEL_ID` | Bump channel ID |
| `DISBOARD_AUTO_BUMP` | `true` |
| `BUMP_TEXT_COMMANDS` | `!d bump,b!bump` (agar aur bhi bump bots hain) |

6. **Create Web Service** → Deploy ho jayega!

---

## ⚙️ Auto Bump Kaise Kaam Karta Hai

```
Bot start hota hai
       ↓
Turant ek baar saare bumps run karta hai
       ↓
Har 30 minute mein check karta hai
       ↓
Agar 2 ghante ho gaye → khud /bump trigger karta hai
       ↓
Disboard confirm kare → timer reset hota hai
       ↓
Cycle repeat...
```

---

## 📋 Bot Permissions Required
- Read Messages / View Channels
- Send Messages
- Embed Links
- Manage Server (invites fetch karne ke liye)
- Read Message History

---

## ❓ Troubleshooting

**Bump kaam nahi kar raha?**
- Check karo `BUMP_CHANNEL_ID` sahi set hai
- Bot ko us channel mein `Send Messages` permission chahiye
- `!forcebump` command use karo manually test karne ke liye

**Invite tracker kaam nahi kar raha?**
- Bot ko `Manage Server` permission chahiye
- Developer Portal mein `Server Members Intent` ON hai?

**Render par bot band ho jata hai?**
- Free tier par Render 15 min mein sleep ho jata hai
- Is issue ke liye ek uptime monitoring service use karo jaise [UptimeRobot](https://uptimerobot.com)
- Ya phir Render ka paid plan use karo
