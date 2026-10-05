<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:8A2BE2,100:4A00E0&height=180&section=header&text=LinkShareBot&fontSize=42&fontColor=ffffff&fontAlignY=38&desc=Secure%20Telegram%20Channel%20Link%20Management%20and%20Auto-Approval%20Engine&descAlignY=58&descSize=18" width="100%" alt="LinkShareBot Header" />

<p align="center">
  <a href="https://t.me/Cosmicbotz">
    <img src="https://i.ibb.co/pBjj8nfW/IMG-20261006-013741.jpg" alt="LinkShareBot Banner" width="100%" style="border-radius: 12px; box-shadow: 0 4px 20px rgba(138, 43, 226, 0.4);" />
  </a>
</p>

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=20&duration=3000&pause=1000&color=9D4EDD&center=true&vCenter=true&width=620&height=45&lines=Zero+Permanent+Link+Leaks;Single-Use+Ephemeral+Invite+Links;Auto-Approve+Join+Requests;Universal+Cloud+%26+VPS+Deployments;Created+by+CosmicBotz" alt="Typing SVG" />
</p>

<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" /></a>
  <a href="https://github.com/TelegramMessenger/Pyrogram"><img src="https://img.shields.io/badge/PyroFork-v2-8A2BE2?style=for-the-badge&logo=telegram&logoColor=white" /></a>
  <a href="https://mongodb.com"><img src="https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white" /></a>
  <a href="https://t.me/Cosmicbotz"><img src="https://img.shields.io/badge/Channel-@Cosmicbotz-blue?style=for-the-badge&logo=telegram&logoColor=white" /></a>
  <a href="https://t.me/JustThreshold"><img src="https://img.shields.io/badge/Dev-@JustThreshold-orange?style=for-the-badge&logo=telegram&logoColor=white" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" /></a>
</p>

</div>

---

## 🌟 Executive Summary

**LinkShareBot** is an enterprise-grade Telegram bot engineered to solve the vulnerability of private channels leaking permanent invite links. When a standard private invite link is posted online, bots, scrapers, and copyright trolls can join or scrape the channel indefinitely.

LinkShareBot completely shields your channels:
1. **Never exposes permanent channel invite URLs.**
2. Generates **single-use ephemeral invite links** (`member_limit=1`) that expire automatically after a configurable time window (`LINK_EXPIRY_SECONDS`, default 5 minutes).
3. Generates **join-request links** (`creates_join_request=True`) paired with an automated approval engine that can approve members instantly or after a timed delay.
4. Enforces an optional **Force-Subscription Gate**, requiring users to join a sponsor channel before receiving their private link.
5. Employs a **pure high-performance PyroFork MTProto engine**: manages high-throughput async event loops, client handlers, and native channel/peer resolution with zero third-party client overhead.

---

## 🚀 Key Feature Highlights

- 🛡️ **Zero Permanent Link Leakage:** Never exposes permanent invite URLs. Generates single-use (`member_limit=1`), time-expiring ephemeral invite links on demand.
- 📩 **Join-Request & Automated Approval Engine:** Supports join-request links (`creates_join_request=True`) with automatic member approval (`/reqmode`, customizable approval timer `/reqtime`).
- ⚡ **Pro Channel Auto-Registration:** When the bot is promoted to administrator in any channel:
  - **Owner Additions:** Registered immediately in MongoDB and invite links are generated automatically.
  - **Admin Additions:** Prompts the admin in private chat with `[✅ Confirm]` and `[❌ Ignore]` buttons to prevent accidental additions.
  - **Config Toggle:** Owner can toggle `ADMIN_DIRECT_ADD` in `/config` to allow instant additions for admins as well.
- ⚙️ **Interactive In-Telegram `/config` Panel:** View and edit settings live in Telegram (Force-Sub, Link Expiry, Rate Limits, Texts, Extra Admins, Deploy Webhook, Direct Add) with clean in-place message updates and one-tap boolean toggles.
- 🔍 **Unified Entity Resolver (`/id`):** Fast native MTProto resolution to resolve any user, channel, supergroup, invite link, username, or forwarded message.
- 🚀 **Universal Cloud & VPS `/update` Engine:**
  - **Cloud Hosting (Koyeb, Render, Heroku):** Triggers redeployment via deploy webhook (`DEPLOY_HOOK_URL`) configured directly in `/config`.
  - **VPS & Local Deployments:** Performs conflict-free Git pull (`git reset --hard`), updates dependencies if `requirements.txt` changed, and cleanly reloads the bot process with reboot state tracking.
- 🛡️ **Non-Admin Security Containment:** Prevents unauthorized users from adding the bot to untrusted channels.
- 🗑️ **Auto-Remove Safety Prompt:** Sends owner an interactive confirmation prompt (`[Confirm Remove]` / `[Keep]`) if the bot is kicked or demoted from a channel.
- 📊 **Complete Moderation Suite:** User bans (`/ban`, `/unban`, `/banlist`), database cleanup, channel JSON export (`/export`), and broadcast with live progress indicator.

---

## 📖 Interactive Documentation & Guides

<details>
<summary><b>🚀 Deployment Guides (Koyeb, Render, VPS, Docker, Local) — [Tap to Open]</b></summary>
<br>

### Option 1: Koyeb (Cloud Container)
1. Fork or push this repository to GitHub.
2. Create a new service on [Koyeb](https://app.koyeb.com).
3. Connect your GitHub repository. Koyeb automatically detects the `Dockerfile`.
4. Configure your environment variables in Koyeb's dashboard.
5. In your Koyeb Service **Settings** ➔ **Deploy** ➔ **Deploy Webhook**, copy the Webhook URL.
6. Open your bot on Telegram and set the webhook URL via `/config` (setting: `DEPLOY_HOOK_URL`).
7. Now whenever you run `/update`, the bot will automatically trigger Koyeb to redeploy the latest commit!

---

### Option 2: Render (Web Service)
1. Create a **Web Service** on [Render](https://render.com).
2. Set Environment to `Docker` or `Python 3`.
3. Set the Health Check path to `/health`.
4. Copy your service's **Deploy Hook** URL into the `DEPLOY_HOOK_URL` setting via `/config`.

---

### Option 3: VPS (Linux / Ubuntu Systemd)
```bash
# 1. Clone repository
git clone https://github.com/Subaru-Natsuki67/Link-Share-Bot.git /opt/linksharebot
cd /opt/linksharebot

# 2. Virtual environment setup
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# 3. Create .env file with your credentials
nano .env

# 4. Create systemd service
sudo nano /etc/systemd/system/linksharebot.service
```

```ini
[Unit]
Description=LinkShareBot Telegram Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/linksharebot
ExecStart=/opt/linksharebot/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable linksharebot
sudo systemctl start linksharebot
```

---

### Option 4: Docker
```bash
# Build Docker image
docker build -t linksharebot .

# Run container with environment file
docker run -d --name linksharebot --env-file .env -p 8080:8080 linksharebot
```

</details>

<details>
<summary><b>⚡ Complete Commands Reference (Public, Admin, Owner) — [Tap to Open]</b></summary>
<br>

### 👤 Public Commands
| Command | Arguments | Permission | Description |
|---|---|---|---|
| `/start` | `[token]` | Public | Starts the bot or resolves a single-use / request deep-link. |
| `/help` | None | Public | Displays instructions and available commands with inline navigation. |
| `/about` | None | Public | Displays information about the bot, version, framework, and maintainer. |
| `/ping` | None | Public | Measures internal bot response latency in milliseconds. |
| `/id` | `[@username \| ID \| link]` | Public | Unified ID tool: resolves caller's ID, replied message/channel, username, or invite link via PyroFork MTProto. |

### 🛠️ Channel Management (Admins)
| Command | Arguments | Permission | Description |
|---|---|---|---|
| `/addch` | `<channel_id>` | Admin | Registers a channel in the bot database and generates initial links. |
| `/delch` | `<channel_id>` | Admin | Removes a channel from the database. |
| `/channels` | None | Admin | Paginated inline channel management panel (toggle auto-approve, get links, delete). |
| `/links` | None | Admin | Lists all normal single-use deep links for registered channels. |
| `/reqlink` | None | Admin | Lists all request-to-join deep links for registered channels. |
| `/bulklink` | `<id1> <id2>...` | Admin | Generates both Normal and Request deep-links for specified channel IDs. |
| `/checkch` | None | Admin | Checks bot admin rights and accessibility for all registered channels. |
| `/top` | None | Admin | Shows top 10 channels ranked by total generated links. |

### 📩 Join Request & Auto-Approval (Admins)
| Command | Arguments | Permission | Description |
|---|---|---|---|
| `/reqmode` | `<channel_id>` | Admin | Toggles automatic approval ON/OFF for a specific channel. |
| `/reqtime` | `[<channel_id>] <seconds>` | Admin | Sets approval delay in seconds (omitting channel sets global default). |
| `/approveon` | None | Admin | Enables automatic join request approval for all channels. |
| `/approveoff` | None | Admin | Disables automatic join request approval for all channels. |

### 🛡️ Moderation & Administration (Admins)
| Command | Arguments | Permission | Description |
|---|---|---|---|
| `/status` | None | Admin | Shows current bot uptime, user count, and channel count. |
| `/users` | None | Admin | Returns the total count of distinct users registered in MongoDB. |
| `/ban` | `<user_id \| reply> [reason]` | Admin | Bans a user from using the bot or generating links. |
| `/unban` | `<user_id \| reply>` | Admin | Lifts ban from a user. |
| `/banlist` | None | Admin | Shows paginated/formatted list of all banned users with reasons. |
| `/export` | None | Admin | Exports all registered channels and their configurations as a JSON file. |
| `/resetlinks` | `<channel_id \| all>` | Admin | Resets link generation counters for one channel or all channels. |
| `/restart` | None | Admin | Cleanly reloads the bot process and updates message on reboot. |

### 👑 Owner Only
| Command | Arguments | Permission | Description |
|---|---|---|---|
| `/stats` | None | Owner | Detailed statistics: user count, channels count, total links generated, bans, uptime. |
| `/broadcast` | *(reply to message)* | Owner/Admin | Broadcasts replied message to all users with live progress indicator. |
| `/cleanup` | None | Owner/Admin | Tests active communication with users and purges deactivated/blocked accounts. |
| `/logs` | None | Owner | Sends the latest `links-sharingbot.txt` log file as an attachment. |
| `/config` | None | Owner | Interactive settings panel to modify runtime settings without restarting. |
| `/update` | None | Owner | Universal update engine: triggers cloud redeploy webhook or pulls latest Git commits. |

</details>

<details>
<summary><b>🔑 Environment Variables Reference — [Tap to Open]</b></summary>
<br>

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_ID` | ✅ Yes | — | Telegram API App ID from [my.telegram.org](https://my.telegram.org). |
| `API_HASH` | ✅ Yes | — | Telegram API Hash from [my.telegram.org](https://my.telegram.org). |
| `TG_BOT_TOKEN` | ✅ Yes | — | Telegram Bot Token from [@BotFather](https://t.me/BotFather). |
| `OWNER_ID` | ✅ Yes | — | Telegram User ID of the primary bot owner. |
| `ADMINS` | ❌ No | `OWNER_ID` | Space-separated list of secondary admin user IDs. |
| `DB_URL` | ✅ Yes | — | MongoDB Atlas / local connection string (`mongodb+srv://...`). |
| `DB_NAME` | ❌ No | `LinkShareBot` | MongoDB database name. |
| `PORT` | ❌ No | `8080` | Port for the aiohttp health-check web server. |
| `FORCE_SUB_CHANNEL` | ❌ No | `0` | Channel ID for the force-subscription gate (`0` = disabled). |
| `LINK_EXPIRY_SECONDS` | ❌ No | `300` | Expiration time for temporary single-use invite links (in seconds). |
| `ADMIN_DIRECT_ADD` | ❌ No | `False` | `True` = Admin-added channels register directly; `False` = Admin must confirm. |
| `DEPLOY_HOOK_URL` | ❌ No | `""` | Webhook URL for cloud redeployment (Koyeb, Render, etc.). Can also be set via `/config`. |
| `LOG_CHANNEL` | ❌ No | `0` | Channel ID for administrative logs and security alerts (`0` = disabled). |
| `START_PICS` | ❌ No | `""` | Comma-separated image URLs displayed randomly on `/start`. |

</details>

<details>
<summary><b>🛡️ Security Architecture & Channel Pipeline Safeguards — [Tap to Open]</b></summary>
<br>

### 1. Owner Direct Add vs. Admin Confirmation Workflow (`plugins/pro_channels.py`)
- **Owner Direct Add**: When the bot is promoted to administrator in a channel by the `OWNER_ID`, it is registered immediately into MongoDB, deep-links (Normal and Request) are generated on the fly, and delivered directly to the Owner via DM and logged to `LOG_CHANNEL`.
- **Admin Confirmation Gate**: When promoted by a secondary admin (`ADMINS`), if `ADMIN_DIRECT_ADD` is `False`, the bot sends an interactive DM to the promoting admin containing channel details and two buttons: `[✅ Confirm]` and `[❌ Ignore]`.
  - Tapping **Confirm** finalizes registration and delivers links.
  - Tapping **Ignore** discards the addition without touching the database.
- **Dynamic Config**: Owner can toggle `ADMIN_DIRECT_ADD` anytime from `/config` with a single tap.

### 2. Non-Admin Channel Addition Containment
- If an unauthorized user promotes the bot to an arbitrary channel, the bot remains in the channel but **skips database registration**, **skips link generation**, and immediately alerts `OWNER_ID` and `LOG_CHANNEL`.

### 3. Auto-Remove on Demotion / Kick
- When the bot is demoted or kicked from a managed channel, it prompts the owner with `[✅ Confirm Remove]` and `[❌ Keep It]` buttons. If ignored for 10 minutes, the prompt auto-expires safely without deleting the channel.

</details>

---

## <code>&lt;/&gt;</code> Credits & Dev Team

> **`sys.maintainers`** — Architecture, core engine engineering, and official network distribution.

<div align="center">

<table>
  <tr>
    <td align="center" width="50%">
      <p><code>// NETWORK & DISTRIBUTION</code></p>
      <h3><code>&lt;CosmicBotz /&gt;</code></h3>
      <p><sub>Updates, announcements & bot ecosystem</sub></p>
      <a href="https://t.me/Cosmicbotz">
        <img src="https://img.shields.io/badge/TELEGRAM-@Cosmicbotz-0088cc?style=for-the-badge&logo=telegram&logoColor=white" alt="CosmicBotz Channel" />
      </a>
    </td>
    <td align="center" width="50%">
      <p><code>// CORE ARCHITECT & DEV</code></p>
      <h3><code>&lt;JustThreshold /&gt;</code></h3>
      <p><sub>Lead Developer & Systems Architect</sub></p>
      <a href="https://t.me/JustThreshold">
        <img src="https://img.shields.io/badge/DEV-@JustThreshold-8A2BE2?style=for-the-badge&logo=telegram&logoColor=white" alt="Lead Dev JustThreshold" />
      </a>
    </td>
  </tr>
</table>

</div>

---

## <code>//</code> License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:8A2BE2,100:4A00E0&height=100" width="100%" />

</div>
