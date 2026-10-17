"""Dokumen project: PRD & BRD.

Struktur bagian mengikuti referensi umum:

- PRD  : Atlassian (participants/status/target release, goals, user stories,
         out-of-scope), Product School, Jama (requirements + traceability),
         ParallelHQ (constraints/dependencies/risks), praktik MoSCoW &
         acceptance criteria "Given-When-Then".
- BRD  : IIBA BABOK (business requirement = goals, objectives, outcomes: "why"
         dan "how success is assessed"), BusinessAnalystMentor, Asana
         (7 komponen BRD), Atlassian. Detail fungsional/teknis diserahkan ke FRD.

Tersedia:
  - `checklist(type)`      -> daftar pertanyaan intak (untuk diisi manusia/agen)
  - `render_structured()`  -> dokumen markdown deterministik dari data terstruktur
  - `build()`              -> prompt (system,user) untuk generate via LLM
  - `fallback()`           -> skeleton bila tidak ada model aktif
"""
import datetime


# ------------------------------------------------------------------ bagian
# (judul, key, tipe render: "para" | "list")
PRD_SPEC = [
    ("Ringkasan & Konteks", "problem", "para"),
    ("Peserta, Status & Target Rilis", "participants", "para"),
    ("Tujuan & Non-Tujuan", "goals", "list"),
    ("Metrik Keberhasilan (Success Metrics)", "metrics", "list"),
    ("Target Pengguna & Persona", "users", "list"),
    ("User Stories & Skenario", "stories", "list"),
    ("Kebutuhan Fungsional", "functional", "list"),
    ("Kebutuhan Non-Fungsional", "nfr", "list"),
    ("Alur Pengguna (User Flow)", "flows", "list"),
    ("Ketergantungan & Keterkaitan", "dependencies", "list"),
    ("Di Luar Cakupan (Out of Scope)", "out_of_scope", "list"),
    ("Rencana Rilis & Milestone", "timeline", "list"),
    ("Asumsi & Pertanyaan Terbuka", "open_questions", "list"),
    ("Risiko & Mitigasi", "risks", "list"),
]

BRD_SPEC = [
    ("Executive Summary", "summary", "para"),
    ("Latar Belakang & Pendorong Perubahan", "background", "para"),
    ("Tujuan & Hasil Bisnis", "objectives", "list"),
    ("Ruang Lingkup (Scope)", "scope", "list"),
    ("Stakeholder & Peran", "stakeholders", "list"),
    ("Kebutuhan Bisnis", "business_reqs", "list"),
    ("Aturan Bisnis (Business Rules)", "business_rules", "list"),
    ("Kebutuhan Fungsional Tingkat Tinggi", "functional", "list"),
    ("Asumsi", "assumptions", "list"),
    ("Batasan (Constraints)", "constraints", "list"),
    ("Kriteria Sukses & KPI", "kpis", "list"),
    ("Risiko & Mitigasi", "risks", "list"),
    ("Analisis Biaya-Manfaat & Timeline", "cost_benefit", "list"),
    ("Persetujuan (Approval)", "approval", "list"),
    ("Glosarium", "glossary", "list"),
]

SPECS = {"PRD": PRD_SPEC, "BRD": BRD_SPEC}
DOCS = {k: [s[0] for s in v] for k, v in SPECS.items()}


# ------------------------------------------------------------------ intak
CHECKLIST = {
    "PRD": [
        {"id": "problem", "section": "Ringkasan & Konteks", "required": True,
         "q": "Masalah atau kesempatan apa yang diselesaikan, dan mengapa sekarang?",
         "hint": "Kondisi saat ini, dampak bila dibiarkan, pemicu perubahan."},
        {"id": "participants", "section": "Peserta & Status", "required": True,
         "q": "Siapa peserta/pengambil keputusan, status, dan target rilis?",
         "hint": "mis. PM: A; Eng lead: B; status: Draft; target: Q1."},
        {"id": "goals", "section": "Tujuan & Non-Tujuan", "required": True,
         "q": "Apa tujuan terukur, dan apa yang secara eksplisit BUKAN tujuan?",
         "hint": "Satu baris per tujuan; tulis juga non-goal agar cakupan tidak melebar."},
        {"id": "metrics", "section": "Metrik Keberhasilan", "required": True,
         "q": "Bagaimana keberhasilan diukur?",
         "hint": "Metrik + cara ukur + target, mis. 'Waktu buat PO < 3 menit'."},
        {"id": "users", "section": "Pengguna & Persona", "required": True,
         "q": "Siapa pengguna utamanya dan kebutuhan intinya?",
         "hint": "Persona/role + kebutuhan + frekuensi pakai."},
        {"id": "stories", "section": "User Stories", "required": True,
         "q": "Ceritakan kebutuhan sebagai user story beserta acceptance criteria.",
         "hint": "Format: 'Sebagai X, saya ingin Y agar Z' + kriteria Given-When-Then."},
        {"id": "functional", "section": "Kebutuhan Fungsional", "required": True,
         "q": "Daftar kebutuhan fungsional (FR) beserta prioritas.",
         "hint": "Beri ID FR-n dan prioritas MoSCoW (Must/Should/Could/Won't)."},
        {"id": "nfr", "section": "Kebutuhan Non-Fungsional", "required": False,
         "q": "Kebutuhan non-fungsional: performa, keamanan, skala, aksesibilitas.",
         "hint": "Sertakan angka target bila ada (mis. respons < 500 ms)."},
        {"id": "flows", "section": "Alur Pengguna", "required": False,
         "q": "Bagaimana alur utama pengguna langkah demi langkah?",
         "hint": "Nomor langkah; sebutkan kondisi gagal/validasi."},
        {"id": "dependencies", "section": "Ketergantungan", "required": False,
         "q": "Apa ketergantungan ke sistem/tim/API lain?",
         "hint": "Sertakan risiko bila dependensi telat."},
        {"id": "out_of_scope", "section": "Di Luar Cakupan", "required": True,
         "q": "Apa yang sengaja TIDAK dikerjakan pada fase ini?",
         "hint": "Mencegah scope creep; sebutkan alasannya singkat."},
        {"id": "timeline", "section": "Rencana Rilis", "required": False,
         "q": "Milestone dan estimasi waktunya?",
         "hint": "Milestone -> deliverable -> estimasi."},
        {"id": "open_questions", "section": "Asumsi & Pertanyaan Terbuka", "required": False,
         "q": "Asumsi apa yang dipakai, dan pertanyaan apa yang masih terbuka?",
         "hint": "Pertanyaan + siapa yang harus menjawab + dampaknya."},
        {"id": "risks", "section": "Risiko", "required": False,
         "q": "Risiko utama dan mitigasinya?",
         "hint": "Risiko -> dampak -> probabilitas -> mitigasi."},
    ],
    "BRD": [
        {"id": "summary", "section": "Executive Summary", "required": True,
         "q": "Ringkas: proyek ini apa, untuk siapa, dan nilai bisnisnya.",
         "hint": "3-5 kalimat untuk pembaca tingkat manajemen."},
        {"id": "background", "section": "Latar Belakang", "required": True,
         "q": "Apa pendorong perubahan dan masalah bisnis saat ini?",
         "hint": "Kondisi sistem/proses sekarang + dampak bisnis bila tidak diubah."},
        {"id": "objectives", "section": "Tujuan Bisnis", "required": True,
         "q": "Tujuan bisnis terukur apa yang ingin dicapai?",
         "hint": "Beri ID BO-n + sasaran terukur + prioritas."},
        {"id": "scope", "section": "Ruang Lingkup", "required": True,
         "q": "Apa yang masuk dan tidak masuk cakupan fase ini?",
         "hint": "Pisahkan In Scope / Out of Scope."},
        {"id": "stakeholders", "section": "Stakeholder", "required": True,
         "q": "Siapa stakeholder, perannya, dan kepentingan utamanya?",
         "hint": "Sertakan siapa yang menyetujui (approver)."},
        {"id": "business_reqs", "section": "Kebutuhan Bisnis", "required": True,
         "q": "Kebutuhan bisnis apa yang harus dipenuhi (bukan solusi teknis)?",
         "hint": "Beri ID BR-n. Fokus pada 'apa & mengapa', bukan 'bagaimana'."},
        {"id": "business_rules", "section": "Aturan Bisnis", "required": False,
         "q": "Aturan/kebijakan bisnis yang membatasi solusi?",
         "hint": "mis. 'PO approved tidak boleh dihapus'."},
        {"id": "functional", "section": "FR Tingkat Tinggi", "required": False,
         "q": "Kebutuhan fungsional tingkat tinggi (opsional).",
         "hint": "Detail teknis sebaiknya masuk FRD, bukan BRD."},
        {"id": "assumptions", "section": "Asumsi", "required": False,
         "q": "Asumsi yang dipakai bila data belum tersedia?",
         "hint": "Tandai status verifikasinya."},
        {"id": "constraints", "section": "Batasan", "required": False,
         "q": "Batasan teknis/bisnis/anggaran/waktu?",
         "hint": "mis. stack wajib, regulasi, kapasitas tim."},
        {"id": "kpis", "section": "Kriteria Sukses & KPI", "required": True,
         "q": "Bagaimana kesuksesan diukur?",
         "hint": "KPI + cara ukur + target + prioritas."},
        {"id": "risks", "section": "Risiko", "required": False,
         "q": "Risiko bisnis/proyek dan mitigasinya?",
         "hint": "Risiko -> dampak -> probabilitas -> mitigasi."},
        {"id": "cost_benefit", "section": "Biaya-Manfaat & Timeline", "required": False,
         "q": "Perkiraan manfaat vs biaya serta timeline?",
         "hint": "Bila angka belum ada, tulis parameternya saja."},
        {"id": "approval", "section": "Persetujuan", "required": False,
         "q": "Siapa yang harus menyetujui dokumen ini?",
         "hint": "Peran + nama + tanggal."},
        {"id": "glossary", "section": "Glosarium", "required": False,
         "q": "Istilah yang perlu didefinisikan?",
         "hint": "Istilah -> definisi."},
    ],
}


def checklist(doc_type):
    doc_type = (doc_type or "PRD").upper()
    if doc_type not in CHECKLIST:
        raise ValueError("doc_type harus PRD atau BRD")
    return {"type": doc_type, "questions": CHECKLIST[doc_type]}


# ------------------------------------------------------------------ render
def _default_title(doc_type, project):
    tag = (project or "project").replace("-", " ").title()
    return f"{doc_type} - {tag}"


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [x for x in v if x is not None and str(x).strip() != ""]
    text = str(v).replace("\r", "")
    out = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line[:2] in ("- ", "* "):
            line = line[2:].strip()
        out.append(line)
    return out


def _fmt_items(items):
    lines = []
    for it in items:
        if isinstance(it, dict):
            parts = [f"**{k}** {v}" for k, v in it.items()
                     if v is not None and str(v).strip() != ""]
            lines.append("- " + " | ".join(parts))
        else:
            lines.append("- " + str(it).strip())
    return "\n".join(lines)


def render_structured(doc_type, project=None, title=None, fields=None,
                      status="Draft", version="0.1", date=None):
    """Bangun markdown deterministik dari data terstruktur (tanpa LLM)."""
    doc_type = (doc_type or "PRD").upper()
    spec = SPECS.get(doc_type)
    if not spec:
        raise ValueError("doc_type harus PRD atau BRD")
    fields = dict(fields or {})
    title = title or _default_title(doc_type, project)
    date = date or datetime.datetime.now().strftime("%Y-%m-%d")

    filled, missing = [], []
    body = []
    for i, (heading, key, kind) in enumerate(spec, start=1):
        val = fields.get(key)
        items = _as_list(val)
        body.append(f"## {i}. {heading}")
        body.append("")
        if kind == "para":
            text = "\n".join(str(x) for x in items).strip()
            if text:
                body += [text, ""]
                filled.append(key)
            else:
                body += ["_(belum diisi)_", ""]
                missing.append(key)
        else:
            if items:
                body += [_fmt_items(items), ""]
                filled.append(key)
            else:
                body += ["- _(belum diisi)_", ""]
                missing.append(key)

    header = [
        f"# {title}", "",
        "| Field | Nilai |", "|---|---|",
        f"| Project | {project or '-'} |",
        f"| Jenis | {doc_type} |",
        f"| Versi | {version} |",
        f"| Tanggal | {date} |",
        f"| Status | {status} |",
    ]
    participants = "\n".join(str(x) for x in _as_list(fields.get("participants")))
    if participants:
        header.append("| Peserta | " + participants.replace("\n", "<br>") + " |")
    header.append("")
    header.append("> Bagian bertanda _(belum diisi)_ perlu dilengkapi. "
                  "Tandai **[Asumsi]** untuk hal yang belum terverifikasi.")
    header.append("")
    content = "\n".join(header + ["---", ""] + body).rstrip() + "\n"
    return {"type": doc_type, "title": title, "project": project,
            "content": content, "filled": filled, "missing": missing,
            "sections": len(spec)}


# ------------------------------------------------------------------ prompt LLM
_REF_GUIDE = {
    "PRD": (
        "Ikuti praktik PRD yang lazim (Atlassian/Product School/Jama): mulai dari "
        "participants-status-target release, problem/why now, goals & non-goals, "
        "success metrics, persona, user stories dengan acceptance criteria "
        "(format Given-When-Then), kebutuhan fungsional ber-ID + prioritas MoSCoW "
        "(Must/Should/Could/Won't), kebutuhan non-fungsional berangka, dependencies, "
        "out-of-scope, milestone, risiko, dan pertanyaan terbuka."
    ),
    "BRD": (
        "Ikuti kerangka BRD (IIBA BABOK + Asana/Atlassian): business requirement = "
        "goals, objectives, outcomes (mengapa perubahan dilakukan dan bagaimana "
        "kesuksesan diukur). Fokus pada 'apa & mengapa', bukan 'bagaimana'. "
        "Sertakan stakeholder + approver, scope in/out, business rules, asumsi, "
        "constraints, KPI, risiko, cost-benefit, dan tanda tangan persetujuan. "
        "Detail fungsional/teknis cukup tingkat tinggi karena rinciannya milik FRD."
    ),
}


def build(doc_type, project=None, title=None, context="", fields=None):
    """Bangun (system, user) prompt untuk menghasilkan PRD/BRD via LLM."""
    doc_type = (doc_type or "PRD").upper()
    spec = SPECS.get(doc_type)
    if not spec:
        raise ValueError("doc_type harus PRD atau BRD")
    title = title or _default_title(doc_type, project)
    sec_list = "\n".join(f"{i+1}. {s[0]}" for i, s in enumerate(spec))
    system = (
        f"Kamu technical writer & business analyst senior. Tulis {doc_type} "
        "berbahasa Indonesia yang lengkap, konkret, dan siap dipakai tim. "
        "Gunakan markdown dengan heading '##' bernomor untuk tiap bagian. "
        + _REF_GUIDE[doc_type] +
        " Jangan mengarang fakta yang tidak diberikan; bila data kurang, tandai "
        "**[Asumsi]** dan masukkan ke Pertanyaan Terbuka. "
        "PENTING: balas HANYA dengan isi dokumen markdown - JANGAN memanggil tool, "
        "JANGAN menjalankan perintah, JANGAN membaca/menulis file."
    )
    parts = []
    if isinstance(fields, dict) and fields:
        for heading, key, _kind in spec:
            items = _as_list(fields.get(key))
            if items:
                parts.append(f"- {heading}: " + " ; ".join(str(x) for x in items))
    user = (
        f"Buat dokumen {doc_type} berjudul \"{title}\""
        + (f" untuk project '{project}'." if project else ".")
        + (f"\n\nKonteks / deskripsi:\n{context.strip()}" if context and context.strip() else "")
        + (("\n\nData yang sudah diketahui:\n" + "\n".join(parts)) if parts else "")
        + f"\n\nWajib memuat bagian berikut secara berurutan:\n{sec_list}\n\n"
        "Untuk tabel gunakan markdown. Beri ID (FR-1, BR-1, NFR-1, KPI-1) dan "
        "prioritas Must/Should/Could/Won't. Tulis acceptance criteria dalam "
        "format Given-When-Then bila relevan."
    )
    return system, user, title


def fallback(doc_type, project=None, title=None, context=""):
    """Skeleton markdown bila tidak ada model aktif."""
    doc_type = (doc_type or "PRD").upper()
    spec = SPECS.get(doc_type, PRD_SPEC)
    title = title or _default_title(doc_type, project)
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    lines = [f"# {title}", "", f"_{doc_type} - dibuat {now}_", ""]
    if context and context.strip():
        lines += ["## Konteks", "", context.strip(), ""]
    for i, (heading, _key, kind) in enumerate(spec, start=1):
        lines += [f"## {i}. {heading}", "",
                  "_(belum diisi)_" if kind == "para" else "- _(belum diisi)_", ""]
    return "\n".join(lines)
