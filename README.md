# AirMCP Solo

AirMCP Solo adalah server **Model Context Protocol (MCP)** lokal yang menggabungkan developer tools, project workspace, multi-agent orchestration, koneksi LLM, dan dashboard visual dalam satu aplikasi Python ringan.

Project ini ditujukan untuk developer yang ingin menjalankan MCP secara mandiri, menguji tool melalui browser, menghubungkan coding client, atau mengatur tim agen AI untuk mengerjakan satu project.

## Fitur utama

- MCP server via STDIO dengan JSON-RPC 2.0 dan capability negotiation.
- Dashboard lokal untuk tools, resources, prompts, chat, agent, project, notes, docs, dan orchestrator.
- Workspace agen 2D dengan status antrean, proses, selesai, gagal, dan dibatalkan.
- Orchestration dalam mode pipeline, debate, dan supervisor.
- Project registry dengan prompt khusus per project di `.mcp/prompts/`.
- Routing LLM untuk OpenAI, DeepSeek, Hermes/OpenRouter, dan provider kustom.
- Tool file, shell, web, Composer, Artisan, SQLite, MySQL, CSV, dan scaffold CRUD.
- Production mode dengan autentikasi, rate limit, sandbox path, security headers, dan proteksi SSRF.
- UI tanpa build step atau CDN; seluruh HTML, CSS, JavaScript, SVG, dan Canvas tersedia lokal.

## Tampilan dan halaman

Jalankan dashboard dengan:

```bash
python dashboard.py
```

Dashboard tersedia di `http://127.0.0.1:8765`. Port akan berpindah otomatis bila 8765 sedang dipakai.

| Halaman | Fungsi |
|---|---|
| Overview | Status server, ringkasan workspace, dan kantor agen 2D |
| Chat | Percakapan dengan provider LLM dan akses tool |
| Orchestrate | Menjalankan tim agen dan memantau run board |
| Agents | Membuat, menjalankan, dan menghapus agen |
| Projects | Membuat, mendaftarkan, dan memilih project |
| Tools | Melihat schema dan menjalankan tool langsung |
| Resources | Membaca resource MCP dan file lokal |
| Prompts | Melihat dan menyelesaikan prompt MCP |
| Docs & Notes | Mengelola dokumentasi serta catatan project |
| Providers | Mengatur koneksi model yang dipakai agen |

## Kebutuhan sistem

- Python 3.10 atau lebih baru
- `pip`
- Git untuk instalasi dari repository
- Node.js hanya untuk test UI JavaScript

Core MCP menggunakan Python standard library. Paket dalam `requirements.txt` dipakai untuk koneksi HTTP dan pemuatan `.env`.

## Instalasi

### Windows

```powershell
git clone https://github.com/muhamadmaulanarizki/AIRMCP.git
cd AIRMCP
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item agents.example.json agents.json
Copy-Item projects.example.json projects.json
python dashboard.py
```

Alternatif melalui Command Prompt:

```cmd
setup.bat
mcp.bat
```

### Linux dan macOS

```bash
git clone https://github.com/muhamadmaulanarizki/AIRMCP.git
cd AIRMCP
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp agents.example.json agents.json
cp projects.example.json projects.json
python dashboard.py
```

`agents.json` dan `projects.json` adalah konfigurasi runtime lokal dan tidak ikut Git. Bila belum ada, aplikasi otomatis memakai konfigurasi `.example.json`.

## Cara menjalankan

### Dashboard web

```bash
python dashboard.py
```

Dashboard menjalankan MCP server sebagai child process, melakukan handshake, lalu membuka browser. Tekan `Ctrl+C` untuk menghentikannya.

### MCP server STDIO

```bash
python mcp_server.py
```

Mode ini digunakan oleh MCP client. `stdout` dikhususkan untuk pesan JSON-RPC.

### Command line client

```bash
python client.py tools
python client.py resources
python client.py prompts
python client.py call list_files path=demo-erp
python client.py resource airmcp://info
python client.py get-prompt code-review "code=x=1/0"
python client.py chat
```

### Terminal UI

```bash
python ui/terminal_ui.py
```

## Integrasi MCP client

Gunakan path absolut menuju `mcp_server.py`. Contoh Windows:

```json
{
  "mcpServers": {
    "airmcp-solo": {
      "command": "python",
      "args": ["C:\\path\\to\\AIRMCP\\mcp_server.py"]
    }
  }
}
```

Contoh Linux/macOS:

```json
{
  "mcpServers": {
    "airmcp-solo": {
      "command": "python3",
      "args": ["/home/user/AIRMCP/mcp_server.py"]
    }
  }
}
```

Server juga menangani client yang mengirim `initialize` tanpa ID atau dengan `id: null`.

## MCP primitives

| Primitive | Dukungan |
|---|---|
| Tools | Discovery, schema, eksekusi, structured content, icon |
| Resources | `file://`, `airmcp://info`, `airmcp://system` |
| Prompts | Prompt bawaan dan prompt Markdown per project |
| Notifications | Started event dan subscription listener |
| Elicitation | Pilihan terstruktur untuk meminta input |

Server menggunakan protocol version `2026-07-28` dan kode error JSON-RPC standar: `-32700`, `-32600`, `-32601`, `-32602`, dan `-32603`.

## Tools

| Kelompok | Tools |
|---|---|
| Filesystem | `list_files`, `read_file` |
| Command | `exec_cmd`, `artisan`, `composer` |
| Network | `web_fetch` |
| Data | `db_sqlite`, `mysql_query`, `csv_stats` |
| Development | `scaffold_crud` |
| Projects | `project_list`, `project_create`, `project_register`, `project_select`, `project_active`, `project_resolve` |
| Project prompts | `project_prompt_list`, `project_prompt_create` |
| Agents | `agent_list`, `agent_create`, `agent_run`, `agent_delete`, `route_agent`, `plan_task`, `orchestrate` |
| Providers | `provider_list`, `provider_create`, `provider_delete`, `llm_chat` |
| Documents | `doc_generate`, `doc_list`, `doc_read`, `doc_delete`, `doc_questions`, `doc_build` |
| Notes | `note_add`, `note_list`, `note_update`, `note_delete` |

Production mode menyembunyikan dan menolak tool berisiko kecuali diizinkan secara eksplisit.

## Project dan prompt lokal

Project disimpan dalam registry lokal `projects.json`. Setiap project dapat menyediakan prompt sendiri:

```text
my-project/
└── .mcp/
    └── prompts/
        ├── mulai-fitur.md
        ├── review-kode.md
        └── tambah-test.md
```

Contoh prompt:

```markdown
---
title: Review Modul
description: Review satu modul secara kritis
required: target
argument: target = file atau folder yang diperiksa
---
Review `{{target}}`, lalu laporkan bug, risiko keamanan, dan rekomendasi.
```

Nama prompt ditampilkan sebagai `<project>/<nama-file>`.

## Agent orchestration

Konfigurasi awal berisi manager, architect, dua engineer, reviewer, tester, technical writer, dan analyst. Edit salinan lokal `agents.json` melalui dashboard atau secara manual.

- `pipeline`: agen bekerja berurutan dan meneruskan hasil.
- `debate`: beberapa agen menganalisis tugas dalam beberapa ronde.
- `supervisor`: agen pertama membuat rencana, mendelegasikan, lalu merangkum hasil.

Tanpa API key, orchestration dapat berjalan dalam mode simulasi agar UI dan alurnya tetap dapat diuji.

## Provider LLM

Salin `.env.example` ke `.env`, lalu isi provider yang diperlukan:

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-chat
HERMES_API_KEY=
OPENROUTER_API_KEY=
HERMES_MODEL=nousresearch/hermes-3-llama-3.1-405b
```

Jangan commit `.env`, `providers.json`, atau token. File tersebut sudah tercakup dalam `.gitignore`.

## Production mode

Contoh PowerShell:

```powershell
$env:AIRMCP_PRODUCTION = "1"
$env:AIRMCP_DASHBOARD_TOKEN = [Convert]::ToHexString(
  [Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
)
$env:AIRMCP_ALLOWED_ROOTS = "C:\workspace\project-a;C:\workspace\project-b"
$env:AIRMCP_HOST = "127.0.0.1"
python dashboard.py
```

Dalam production mode:

- dashboard memakai HTTP Basic Authentication;
- password adalah `AIRMCP_DASHBOARD_TOKEN`, username boleh bebas;
- API dibatasi per IP;
- akses file dibatasi ke project terdaftar dan `AIRMCP_ALLOWED_ROOTS`;
- `web_fetch` menolak localhost, loopback, link-local, dan private network;
- response dashboard mengirim security headers;
- tool berisiko diblokir secara default.

Aktifkan tool tertentu jika memang dibutuhkan:

```powershell
$env:AIRMCP_ALLOWED_DANGEROUS_TOOLS = "web_fetch,scaffold_crud"
```

Bind selain localhost mewajibkan token. Gunakan reverse proxy HTTPS bila dashboard diakses melalui jaringan.

Health probe tanpa autentikasi:

```text
GET /healthz
GET /readyz
```

## Environment variables

| Variable | Default | Fungsi |
|---|---:|---|
| `AIRMCP_PRODUCTION` | `0` | Aktifkan kebijakan production |
| `AIRMCP_DASHBOARD_TOKEN` | kosong | Password dashboard dan syarat bind non-local |
| `AIRMCP_HOST` | `127.0.0.1` | Host dashboard |
| `AIRMCP_PORT` | `8765` | Port awal dashboard |
| `AIRMCP_RATE_LIMIT_PER_MINUTE` | `240` | Batas request API per IP per menit |
| `AIRMCP_ALLOWED_ROOTS` | kosong | Tambahan root filesystem yang diizinkan |
| `AIRMCP_ALLOWED_DANGEROUS_TOOLS` | kosong | Allowlist tool berisiko |
| `AIRMCP_ALLOW_PRIVATE_NETWORK` | `0` | Izinkan fetch ke private network |
| `AIRMCP_NO_BROWSER` | `0` | Jangan buka browser otomatis |
| `AIRMCP_TRACE` | kosong | Path trace log MCP |

## Struktur repository

```text
AIRMCP/
├── mcp_server.py          # MCP server dan tool registry
├── jsonrpc.py             # JSON-RPC message layer
├── dashboard.py           # HTTP server dan bridge MCP
├── security.py            # Kebijakan production
├── orchestrator.py        # Multi-agent workflow
├── providers.py           # Provider registry dan HTTP client
├── projects.py            # Project registry dan prompt lokal
├── documents.py           # Document workspace
├── client.py              # CLI client
├── ui/
│   ├── dashboard.html     # Dashboard SPA
│   ├── agent_stage.js     # Canvas workspace 2D
│   ├── run_state.js       # State machine run board
│   └── terminal_ui.py
├── demo-erp/              # Project contoh dan fixture integrasi
├── tests/                 # Integration, HTTP, reliability, UI, production
├── agents.example.json
├── projects.example.json
├── .env.example
├── setup.bat
└── mcp.bat
```

## Testing

Semua test Python di Windows:

```powershell
$python = if (Test-Path .\.venv\Scripts\python.exe) { ".\.venv\Scripts\python.exe" } else { "python" }
Get-ChildItem tests\test_*.py | ForEach-Object { & $python $_.FullName }
```

Test UI JavaScript:

```bash
node tests/test_dashboard_ui.cjs
node tests/test_agent_stage.cjs
node tests/test_run_state.cjs
```

Suite mencakup handshake dan dialect MCP, JSON-RPC errors, resources, prompts, tools, dashboard API, orchestration, reliability, production security, dan state UI.

## Troubleshooting

### Dashboard tidak terbuka

Periksa output terminal untuk alamat aktual. Tentukan port secara manual bila perlu:

```powershell
$env:AIRMCP_PORT = "9000"
python dashboard.py
```

### Provider tidak aktif

Pastikan `.env` ada, key tidak kosong, dan nama model sesuai akun provider. Restart dashboard setelah mengubah environment variable.

### MCP client gagal menjalankan server

- gunakan path absolut ke `mcp_server.py`;
- pastikan executable Python dapat dipanggil oleh client;
- gunakan Python virtual environment jika dependensi terpasang di sana;
- jalankan `python tests/test_strict_client.py` untuk memeriksa spawn dan handshake.

### Project tidak ditemukan

Daftarkan folder melalui halaman Projects atau tool `project_register`. Path relatif di `projects.example.json` diselesaikan dari root repository.

## Keamanan

AirMCP dapat menjalankan command dan membaca file lokal. Jalankan pada mesin dan project yang Anda percaya. Untuk akses jaringan atau penggunaan bersama, aktifkan production mode, batasi allowed roots, gunakan token kuat, dan tempatkan dashboard di belakang HTTPS.

## Kontribusi

Issue dan pull request diterima. Sertakan deskripsi perubahan, langkah reproduksi untuk bug, dan hasil test yang relevan.
