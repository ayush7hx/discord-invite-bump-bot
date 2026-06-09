# 🤖 Discord Invite & Bump Bot

A Discord bot with **Invite Tracker** and **Auto Bump Reminder** features.

---

## ✨ Features

### 1. 📨 Invite Tracker
- Jab bhi koi naya member join kare, ek embed message send hoga jo batayega:
  - Kaun join hua
  - Kisne invite kiya
  - Inviter ke total invites kitne hain

### 2. ⏰ Auto Bump Reminder
- Disboard ke `/bump` command ka use detect karta hai
- ठीक 2 hours baad automatically bump reminder send karta hai channel mein
- Role mention bhi kar sakta hai (optional)

### 3. 🛠️ Extra Commands
- `!invites [@user]` - Kisi member ke total invites check karo
- `!bumptimer` - Dekho kitni der mein next bump available hai

---

## 🚀 Setup Guide

### Step 1: Discord Bot Banana
1. [Discord Developer Portal](https://discord.com/developers/applications) par jao
2. **New Application** click karo
3. **Bot** section mein jao → **Add Bot**
4. **Token** copy karo
5. **Privileged Gateway Intents** mein ye enable karo:
   - ✅ Server Members Intent
   - ✅ Message Content Intent

### Step 2: Bot ko Server mein Add Karo
Ye link use karo (apna CLIENT_ID daalo):
```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot
```

### Step 3: Environment Variables Set Karo
`.env.example` copy karke `.env` banao:
```bash
cp .env.example .env
```

Phir apni values daalo:
```env
DISCORD_TOKEN=your_bot_token_here
INVITE_CHANNEL_ID=channel_id_jahan_invite_log_aaye
BUMP_CHANNEL_ID=channel_id_jahan_bump_reminder_aaye
BUMP_ROLE_ID=role_id_jo_ping_ho_bump_reminder_mein
```

#### Channel/Role ID kaise milega?
1. Discord Settings → Advanced → **Developer Mode ON** karo
2. Kisi bhi channel par right-click → **Copy ID**

---

## ☁️ Render Par Deploy Karna (24/7 Free)

1. [render.com](https://render.com) par account banao
2. **New → Blueprint** click karo
3. Is GitHub repo ko connect karo
4. Environment variables add karo:
   - `DISCORD_TOKEN`
   - `INVITE_CHANNEL_ID`
   - `BUMP_CHANNEL_ID`
   - `BUMP_ROLE_ID` (optional)
5. **Deploy** karo!

---

## 📋 Bot Permissions Required
- Read Messages / View Channels
- Send Messages
- Embed Links
- Manage Guild (invites fetch karne ke liye)
- Read Message History

---

## ⚠️ Important Notes
- Bot ko **Manage Server** permission chahiye invite tracking ke liye
- Disboard ka `/bump` use karo — bot automatically 2 hours baad remind karega
- Agar bump channel auto-detect na ho, `BUMP_CHANNEL_ID` set karo `.env` mein
