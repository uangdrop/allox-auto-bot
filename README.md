# Allox Auto Bot 🤖

> Auto-login pakai Web3 wallet signature, auto-chat ke AI, dan farming
> point dari [Allox](https://allox.ai) — dengan laporan Telegram tiap
> 24 jam (opsional).

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Edukasi-orange)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey)

---

## ⚡ Paling cepetan (TL;DR)

```bash
git clone https://github.com/uangdrop/allox-auto-bot.git
cd allox-auto-bot
source ./activate.sh        # otomatis deteksi OS, install deps, bikin venv
cp accounts.txt.example accounts.txt
nano accounts.txt           # isi private key, simpan (Ctrl+O, Enter, Ctrl+X)
python bot.py
```

`activate.sh` self-contained: dia **auto-detect OS** lo (Ubuntu/Debian,
Fedora, Arch, Alpine, macOS), cek apakah `python3-venv` udah keinstall,
kalo belum **otomatis install** (dengan konfirmasi), terus bikin venv +
install requirements. Kalo ada error, dia kasih instruksi fix yang
spesifik buat OS lo.

**Pengen di Windows / tanpa git / multi-user setup?**
Lanjut ke [🚀 Cara pakai lengkap](#-cara-pakai-lengkap).

---

## ✨ Fitur

- 🔐 **Login Web3 signature** — tanpa password, sign nonce dari server
  pakai `eth-account`
- 💬 **Auto-chat** — sampai **20 pesan per akun per siklus 24 jam**
- 📰 **Prompt crypto multi-source** — 4 RSS feed (Cointelegraph, Coindesk,
  Decrypt, Bitcoin.com), diacak tiap siklus, dibungkus natural language
  biar kelihatan kayak pertanyaan user
- 🌐 **Support proxy** — HTTP/HTTPS, dengan auth, opsional per run
- 📊 **Live point tracking** — log terminal berwarna, zona waktu
  `Asia/Jakarta` (WIB)
- 🔁 **Auto-cycle** — semua akun selesai → tidur 24 jam → ulang lagi
- 📩 **Laporan Telegram** *(opsional)* — ringkasan siklus harian
  dikirim ke chat lo

---

## 📁 Struktur project

```
allox-auto-bot/
├── bot.py                  ← entry point
├── telegram.py             ← reporter Telegram (opsional)
├── activate.sh             ← shortcut: auto-bikin venv + install
├── requirements.txt
├── .env.example            ← copy ke .env
├── accounts.txt.example    ← copy ke accounts.txt
├── proxy.txt.example       ← copy ke proxy.txt
├── .gitignore
├── LICENSE                 ← MIT
└── README.md
```

> ⚠️ **JANGAN PERNAH commit** `accounts.txt`, `proxy.txt`, `.env`, atau
> file `*.session`. Semuanya udah di-exclude `.gitignore`.

---

## 🚀 Cara pakai lengkap

### 1. Syarat

- **Python 3.10 atau lebih baru**
  - Cek: `python3 --version`
  - Di Ubuntu 24.04+ / Debian 12+ udah include Python 3.12 bawaan
  - Di Windows: download dari [python.org](https://www.python.org/downloads/)
- **Git** (atau download manual dari GitHub → Code → Download ZIP)
- Daftar **private key Ethereum** (satu per wallet yang mau lo farming)

### 2. Clone repo

**Pake git (direkomendasikan):**

```bash
git clone https://github.com/uangdrop/allox-auto-bot.git
cd allox-auto-bot
```

**Atau download ZIP:**

1. Buka halaman repo di GitHub
2. Klik tombol hijau **Code** → **Download ZIP**
3. Extract ZIP ke folder mana aja
4. Buka terminal/cmd di folder itu

### 3. Bikin virtual environment + install dependencies

**Cara gampang (Linux/macOS/WSL)** — pake script `activate.sh`:

```bash
source ./activate.sh
```

Script ini otomatis:

- 🔍 **Deteksi OS** lo (Ubuntu/Debian/Fedora/Arch/Alpine/macOS) + package
  manager yang sesuai (apt/dnf/pacman/apk/brew)
- 🐍 **Cek Python** — versi minimal 3.10
- 📦 **Cek `python3-venv`** — kalau belum keinstall, script nanya
  konfirmasi buat auto-install via package manager
- 🏗️ **Bikin `.venv`** kalo belum ada (atau rebuild kalo corrupt)
- 📥 **Install requirements.txt** (sekali aja, idempotent)
- ✅ **Verifikasi** semua module critical bisa di-import
- 🎨 **Banner + warna** biar output gampang dibaca

Kalau aktivasi sukses, prompt lo bakal jadi:
```
(.venv) user@server:~/allox-auto-bot$
```
Dan output akhir:
```
╔════════════════════════════════════════╗
║   ✓  Environment siap dipakai!        ║
╚════════════════════════════════════════╝

  python : /home/user/allox-auto-bot/.venv/bin/python
  pip    : /home/user/allox-auto-bot/.venv/bin/pip
  cwd    : /home/user/allox-auto-bot

  Lanjut :  python bot.py
  Stop   :  deactivate
```

**Cara manual** (kalo `activate.sh` gak bisa dipake):

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Windows (cmd)
python -m venv .venv
.venv\Scripts\activate.bat

# Terus install (semua OS sama)
pip install --upgrade pip
pip install -r requirements.txt
```

> **Error `externally-managed-environment`?**
> Itu artinya Python lo (kemungkinan Ubuntu 24.04+ / Python 3.12) ngunci
> pip system-wide. Solusi: **pake virtual environment** kayak step di
> atas. JANGAN pake `pip install --break-system-packages` kecuali lo
> ngerti konsekuensinya.

> **Error `python3-venv not available` atau `.venv/bin/activate: No such file`?**
> Itu artinya package `python3-venv` belum keinstall di Ubuntu/Debian lo.
> Fix:
> ```bash
> sudo apt install -y python3-venv python3-full
> rm -rf .venv
> source ./activate.sh
> ```
> Script `activate.sh` udah include deteksi otomatis + pesan error yang
> nunjukin fix yang bener buat OS lo (Ubuntu/Fedora/macOS).

### 4. Konfigurasi akun

```bash
cp accounts.txt.example accounts.txt
```

Edit `accounts.txt` pake text editor apa aja (nano, vim, VS Code):

```bash
nano accounts.txt
```

Isi satu private key per baris:

```
# Format: 0x + 64 karakter hex (0x prefix boleh ngga)
0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
0xabcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789ab
```

Di nano: `Ctrl+O` → `Enter` buat simpan, `Ctrl+X` buat keluar.

> ⚠️ **PENTING**: Jangan kasih orang lain `accounts.txt`. Isi private
> key = kontrol penuh atas wallet.

### 5. (Opsional) Konfigurasi proxy

Kalo lo mau pake proxy (mis. buat handle rate-limit, atau sembunyiin
IP):

```bash
cp proxy.txt.example proxy.txt
nano proxy.txt
```

Format (satu proxy per baris):

```
http://user:password@127.0.0.1:8080
https://1.2.3.4:443
http://10.0.0.1:3128          # tanpa auth juga boleh
```

### 6. Jalankan bot

```bash
python bot.py
```

Pas pertama kali, lo ditanya mode proxy:

```
[19:00:00] [INFO] Select run mode:
  1. Run with proxy
  2. Run without proxy
Choice [1/2]: _
```

Ketik `1` atau `2`, tekan Enter. Pilihan lo disimpan ke `.allox_state.json`
— jadi nggak ditanya lagi di run berikutnya.

Output normal bakal kayak gini:

```
[19:42:08] [SUCCESS] Loaded 2 account(s) from accounts.txt
[19:42:08] [SUCCESS] RSS: 30 titles from https://cointelegraph.com/rss
[19:42:08] [INFO] ── Account 1/2 ──
[19:42:08] [INFO] Wallet: 0xFCAd0B19bB29D4674531d6f115237E16AfCE377c
[19:42:10] [SUCCESS] Logged in: 0xFCAd...377c
[19:42:13] [SUCCESS] Chat 1/20 Sent | +10 Pts | Total: 10 | Limit: 19
[19:42:16] [SUCCESS] Chat 2/20 Sent | +10 Pts | Total: 20 | Limit: 18
...
[20:00:00] [INFO] Cycle #1: 2/2 akun sukses, 0 gagal.
[20:00:00] [INFO] Cycle complete. Sleeping 24h — next run at 2026-07-13 20:00:00 WIB
```

Tekan `Ctrl+C` kapan aja buat stop.

### 7. Run ulang / auto-restart

Bot-nya jalan forever (cycle 24 jam). Kalo lo mau:

- **Jalan manual tiap hari**: `source .venv/bin/activate && python bot.py`
- **Jalan di background (Linux)**: `nohup python bot.py > bot.log 2>&1 &`
- **Auto-start pas server reboot**: pake `systemd` atau `cron @reboot`
  (lihat [Deployment](#-deployment) di bawah)

---

## 📩 Laporan Telegram (opsional)

Laporan Telegram **mati secara default**. Buat nyalain:

### Opsi A — Bot API (recommended, paling gampang)

1. Buka Telegram, chat [@BotFather](https://t.me/BotFather), kirim `/newbot`
2. Ikutin instruksi, copy **token** yang dikasih
3. Buka chat sama bot baru lo, kirim `/start` (**wajib!**)
4. Dapetin **chat_id** lo dari [@userinfobot](https://t.me/userinfobot)
5. Bikin file `.env`:

   ```bash
   cp .env.example .env
   nano .env
   ```

   Isi:

   ```env
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   TELEGRAM_CHAT_ID=123456789
   ```

6. Restart bot: `python bot.py`

### Opsi B — Telethon userbot (advanced)

Pake ini cuma kalau lo perlu post ke channel/group atas nama akun lo
sendiri. Resiko rate-limit / akun ke-restrict lebih tinggi.

```env
TELEGRAM_API_ID=12345
TELEGRAM_API_HASH=abcdef0123456789...
TELEGRAM_SESSION=allox_reporter
TELEGRAM_CHAT_ID=123456789
```

> `TELEGRAM_SESSION` itu nama file (nggak pake path) — Telethon bikin
> otomatis pas run pertama dan minta nomor HP lo. Cuma sekali aja.

### Format laporan

Tiap 24 jam, lo bakal dapet pesan kayak gini di Telegram:

```
📊 Allox Auto Bot — Cycle #1 Report
🕐 2026-07-12 19:00:00 WIB → 2026-07-12 19:42:00 WIB

───────────────────────────────────────────
| Akun sukses  | 1                          |
| Akun gagal   | 2                          |
───────────────────────────────────────────

⚠️ Detail Kegagalan
  • 0xFCAd...377c — Invalid private key length: 8 hex chars (expected 64)
  • 0x9B12...aa91 — Failed to fetch nonce (network / proxy / API error)

🛠 Solusi Umum
  • Invalid private key length: ... → Cek format key di accounts.txt — harus 64 hex char (0x prefix opsional).
  • Failed to fetch nonce ... → Cek koneksi/proxy, atau tunggu beberapa menit.
```

> **Tips multi-user**: Kalo lo jalanin bot untuk beberapa orang (temen,
> komunitas), tiap orang bikin **bot Telegram sendiri** + simpen
> `.env`-nya sendiri. 1 token bot = 1 report channel. Jangan share
> 1 token untuk banyak orang — semua report bakal ke-merge jadi 1 chat.

---

## ⚙️ Referensi konfigurasi

Semua setting dibaca dari environment variable (atau `.env`).

| Variable               | Default                        | Keterangan                          |
|------------------------|--------------------------------|--------------------------------------|
| `ALLOX_API_BASE`       | `https://api.allox.ai/v1`      | Root API (override untuk testnet)   |
| `RSS_FEEDS`            | *(lihat di bawah)*             | Daftar RSS, pisahkan pakai koma      |
| `PROMPT_TEMPLATES`     | *(lihat di bawah)*             | Template prompt, pisahkan pakai `\|` |
| `TELEGRAM_BOT_TOKEN`   | *(kosong)*                     | Token Bot API                       |
| `TELEGRAM_CHAT_ID`     | *(kosong)*                     | Target chat / user / channel        |
| `TELEGRAM_API_ID`      | *(kosong)*                     | Telethon api_id                     |
| `TELEGRAM_API_HASH`    | *(kosong)*                     | Telethon api_hash                   |
| `TELEGRAM_SESSION`     | *(kosong)*                     | Nama file session Telethon          |
| `TELEGRAM_PARSE_MODE`  | `HTML`                         | `HTML`, `Markdown`, atau kosong     |

Kalau `TELEGRAM_BOT_TOKEN` dan variabel Telethon di-set barengan, Bot
API yang dipake.

### RSS feed

Default feed-nya:

```
https://cointelegraph.com/rss
https://www.coindesk.com/arc/outboundfeeds/rss/
https://decrypt.co/feed
https://news.bitcoin.com/feed/
```

Tiap siklus, feed di-coba **urutannya diacak** — jadi kalau satu mati
atau ke-rate-limit, feed berikutnya langsung ngeganti. Judul yang
sama dari feed berbeda di-dedup.

Buat pake feed sendiri, set `RSS_FEEDS` di `.env`:

```env
RSS_FEEDS=https://cointelegraph.com/rss,https://decrypt.co/feed,https://my-fav-feed.example.com/rss
```

### Template prompt

Judul mentah dibungkus di template natural language secara acak, biar
keliatan kayak pertanyaan user bukan copy-paste judul berita. Template
default:

```
Can you explain this crypto news: {title}?
What are your thoughts on this event: {title}?
Summarize the impact of this headline: {title}
Is this bullish or bearish for the market: {title}?
Provide a brief analysis on this news: {title}
```

Buat customize, set `PROMPT_TEMPLATES` di `.env` (pake `|` sebagai
pemisah, `{title}` jadi placeholder):

```env
PROMPT_TEMPLATES=Jelasin headline ini: {title}|Menurut lo gimana: {title}?|Ringkas berita ini: {title}
```

---

## 🛠 Deployment

### Opsi 1 — `screen` / `tmux` (paling gampang)

```bash
# Install screen
apt install -y screen        # Ubuntu/Debian
brew install screen          # macOS

# Bikin session baru
screen -S allox

# Di dalam screen, jalanin bot
cd ~/allox-auto-bot
source .venv/bin/activate
python bot.py

# Detach: Ctrl+A, terus D
# List session: screen -ls
# Reattach:  screen -r allox
```

### Opsi 2 — `nohup` (background, output ke file)

```bash
cd ~/allox-auto-bot
source .venv/bin/activate
nohup python bot.py > bot.log 2>&1 &

# Liat log
tail -f bot.log

# Stop
pkill -f "python bot.py"
```

### Opsi 3 — `systemd` (auto-start pas reboot, production-grade)

Bikin file `/etc/systemd/system/allox-bot.service`:

```ini
[Unit]
Description=Allox Auto Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/allox-auto-bot
ExecStart=/root/allox-auto-bot/.venv/bin/python /root/allox-auto-bot/bot.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/allox-bot.log
StandardError=append:/var/log/allox-bot.log

[Install]
WantedBy=multi-user.target
```

Aktifin:

```bash
sudo systemctl daemon-reload
sudo systemctl enable allox-bot
sudo systemctl start allox-bot
sudo systemctl status allox-bot       # cek status
sudo journalctl -u allox-bot -f       # liat log realtime
```

> **Penting**: ganti `User=root` dan `WorkingDirectory` sesuai setup
> lo. Kalo lo pake user lain, bikin `chown -R user:user /path/to/project`.

---

## 🛠 Troubleshooting

| Masalah                                   | Solusi                                                                 |
|-------------------------------------------|------------------------------------------------------------------------|
| `No nonce in response`                    | Skema API berubah. Edit `request_nonce()` di `bot.py`.                |
| `No token in response`                    | Skema API berubah. Edit `login()` di `bot.py`.                        |
| `Proxy error` / `SSL error`               | Proxy-nya mati. Ganti di `proxy.txt` atau jalan tanpa proxy.          |
| `Request failed after 3 attempts`         | Network/timeout. Cek internet, coba proxy lain.                       |
| `Invalid private key length`              | Key di `accounts.txt` salah. Harus 64 hex char (0x boleh, boleh ngga).|
| `Signing failed`                          | `pip install -U eth-account`                                          |
| `error: externally-managed-environment`   | Ubuntu 24.04+ / Python 3.12 ngunci pip system-wide. Solusi:           |
|                                           | `python3 -m venv .venv && source .venv/bin/activate` lalu install     |
|                                           | ulang, atau pake `source ./activate.sh`. Alternatif terakhir:          |
|                                           | `pip install --break-system-packages -r requirements.txt`.            |
| `python3-venv not available` atau          | Package `python3-venv` belum keinstall. Fix:                          |
| `.venv/bin/activate: No such file`        | `sudo apt install -y python3-venv python3-full && rm -rf .venv &&     |
|                                           | source ./activate.sh`. Script `activate.sh` udah deteksi otomatis    |
|                                           | dan ngasih pesan fix yang sesuai OS lo.                                |
| `All RSS feeds failed`                    | Semua sumber RSS down. Bot fallback ke prompt statis dan tetap jalan. |
|                                           | Cek internet, atau override `RSS_FEEDS` ke feed yang masih hidup.     |
| `Only got N prompts from RSS, padding`    | Beberapa feed balikin lebih sedikit dari yang diharapkan. Siklus tetap |
|                                           | jalan normal.                                                          |
| Telegram: laporan nggak masuk             | Cek nilai `.env`. Buat Bot API, pastikan udah kirim `/start` ke bot. |
| Telegram: `HTTP 400 parse error`          | Set `TELEGRAM_PARSE_MODE=` (kosong) buat fallback ke plain text.       |
| Bot-nya jalan tapi dapet point 0          | Kemungkinan kena rate-limit server. Tunggu 24 jam cycle berikutnya.   |
|                                           | Atau cek `accounts.txt` ada key yang valid.                            |

---

## 🔒 Keamanan

- **Private key itu SANGAT sensitif.** Siapapun yang punya key lo,
  bisa kontrol wallet-nya. Jangan pernah share `accounts.txt`, jangan
  commit, jangan upload ke tempat publik.
- `.gitignore` udah exclude `accounts.txt`, `proxy.txt`, `.env`, dan
  `*.session`. Tetap double-check sebelum tiap commit: `git status`
  nggak boleh nampilin file-file itu.
- Jalanin di mesin yang lo percaya. Jangan paste key di shared/cloud
  VM yang nggak lo kontrol.
- **Kalo lo distribusiin bot ini ke banyak orang** (temen, komunitas):
  - Masing-masing orang bikin `accounts.txt` & `.env` sendiri
  - Jangan share file yang ada private key
  - Bot Telegram harus 1 per orang, jangan dipake bareng
- Project ini **edukatif**. Pake dengan risiko sendiri dan hormati
  Terms of Service platform target.

---

## 🤝 Buat yang mau kontribusi

```bash
# Fork repo lo, terus:
git clone https://github.com/uangdrop/allox-auto-bot.git
cd allox-auto-bot
git checkout -b feature/nama-fitur

# ... edit kode ...

git add -A
git commit -m "Tambah: <deskripsi>"
git push origin feature/nama-fitur
# Buka Pull Request di GitHub
```

---

## 📜 Lisensi

MIT — lihat [LICENSE](LICENSE).
