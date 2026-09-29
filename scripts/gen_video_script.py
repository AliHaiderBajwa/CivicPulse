#!/usr/bin/env python3
"""Generate the J4 video shooting script: a tabular .docx (for the narrator's
screen) and a numbered .txt (for the operator to copy/paste). One source of
truth so the two can never disagree."""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
DOCX_OUT = ROOT / "docs" / "VIDEO-SCRIPT-J4.docx"
TXT_OUT = ROOT / "docs" / "VIDEO-SCRIPT-COMMANDS.txt"

# ---------------------------------------------------------------- commands --
# id -> (text, note, which beat/step uses it)
COMMANDS: dict[str, tuple[str, str]] = {
    "P01": ("grep -E '^TRIAGE_PROVIDER|^LLM_MODEL' .env",
            "MUST print TRIAGE_PROVIDER=llm and LLM_MODEL=openai/gpt-oss-120b"),
    "P02": ("docker compose up -d", "starts the compose stack (idempotent)"),
    "P03": ("curl -s -o /dev/null -w 'compose:%{http_code}\\n' http://localhost:8080/",
            "MUST print compose:200"),
    "P04": ("curl -s -o /dev/null -w 'k3d:%{http_code}\\n' http://civicpulse.localhost:8081/",
            "MUST print k3d:200"),
    "C01": ('cd ~/Desktop/"SCD A1"/CivicPulse', "move into the project folder"),
    "C02": ("git clone https://github.com/AliHaiderBajwa/CivicPulse.git", "clone the repo"),
    "C03": ("cd CivicPulse", "enter the cloned folder"),
    "C04": ("docker compose up -d --build", "BEAT 2 - build + start all services"),
    "C05": ("docker compose ps", "BEAT 2 - show all four services healthy"),
    "C06": ("sed -i 's/^TRIAGE_PROVIDER=.*/TRIAGE_PROVIDER=simulated/' .env",
            "BEAT 4 - force the fallback provider"),
    "C07": ("docker compose up -d --force-recreate backend",
            "BEAT 4 - restart backend with fallback, wait for 'healthy'"),
    "C08": ("curl -s -X POST http://localhost:8000/api/complaints "
            "-H 'Content-Type: application/json' "
            "-d '{\"text\":\"Water main burst flooding the street near the school\","
            "\"location\":\"Block 4, Street 12\"}' | python3 -m json.tool",
            "BEAT 4 - same complaint, must show triaged_by: simulated"),
    "C09": ("docker compose ps --format '{{.Service}}  {{.Ports}}'",
            "BEAT 5 - show only the web tier is published"),
    "C10": ('curl -s -m 3 -o /dev/null -w "db(5432):%{http_code}\\n" http://localhost:5432',
            "BEAT 5 - MUST print 000 (refused)"),
    "C11": ('curl -s -m 3 -o /dev/null -w "redis(6379):%{http_code}\\n" http://localhost:6379',
            "BEAT 5 - MUST print 000 (refused)"),
    "C12": ("docker compose down", "BEAT 6 - stop compose, switch to Kubernetes"),
    "C13": ("kubectl -n civicpulse get pods", "BEAT 6 - all pods running"),
    "C14": ("kubectl -n civicpulse get hpa -w",
            "BEAT 6 - TERMINAL A, leave running the whole beat"),
    "C15": ("BASE_URL=http://civicpulse.localhost:8081 k6 run scripts/load/burst.js",
            "BEAT 6 - TERMINAL B, the load generator"),
    "C16": ("kubectl -n civicpulse rollout history deployment/backend",
            "BEAT 7 - show revision history"),
    "C17": ("kubectl -n civicpulse rollout restart deployment/backend",
            "BEAT 7 - creates the new revision (REQUIRED before undo)"),
    "C18": ("kubectl -n civicpulse rollout status deployment/backend",
            "BEAT 7 - wait for green"),
    "C19": ("kubectl -n civicpulse rollout undo deployment/backend",
            "BEAT 7 - roll back to previous revision"),
    "C20": ("kubectl -n civicpulse rollout status deployment/backend",
            "BEAT 7 - wait for green again"),
    "C21": ('curl -s -o /dev/null -w "still-serving:%{http_code}\\n" '
            'http://civicpulse.localhost:8081/',
            "BEAT 7 - MUST print still-serving:200"),
    "A01": ("sed -i 's/^TRIAGE_PROVIDER=.*/TRIAGE_PROVIDER=llm/' .env",
            "AFTER - restore the live LLM"),
    "A02": ("docker compose up -d", "AFTER - bring the compose stack back"),
}

# -------------------------------------------------------------------- beats --
# (beat title, duration, rows) ; row = (time, who, on-screen, words, [cmds])
BEATS: list[tuple[str, str, list[tuple[str, str, str, str, list[str]]]]] = [
    ("BEAT 1 - CLONE THE PROJECT", "0:30 (0:00-0:30)", [
        ("0:00", "ALI",
         "Chrome: show github.com/AliHaiderBajwa/CivicPulse for 2s, then Alt+Tab to the "
         "terminal. Paste C01 then C02. Leave the clone output scrolling.",
         "This is CivicPulse - a civic issue reporting system, built by the two of us. "
         "It takes a citizen complaint, triages it with AI, and routes it to the right "
         "department.",
         ["C01", "C02"]),
        ("0:15", "ASHAR",
         "Terminal: the clone finishes. Paste C03. Keep the prompt visible.",
         "It's fully containerized, tested end to end, and it ships through GitHub "
         "Actions. Let me show you it running.",
         ["C03"]),
    ]),
    ("BEAT 2 - RUNNING SYSTEM", "0:30 (0:30-1:00)", [
        ("0:30", "ASHAR",
         "Terminal: paste C04. Wait for the healthy checks. Say nothing about the "
         "build noise - let it finish.",
         "One command brings up Postgres, Redis, the FastAPI backend, and the frontend. "
         "Four healthy services in about fifteen seconds.",
         ["C04"]),
        ("0:42", "ALI",
         "Paste C05, point at the four 'healthy' entries. Then Alt+Tab to Chrome and "
         "open http://localhost:8080 - show the Dashboard, then click Submit.",
         "Open at localhost port 8080 - that's the dashboard. Every complaint on it is "
         "real data from Postgres, not mockups.",
         ["C05"]),
    ]),
    ("BEAT 3 - AI TRIAGE (the money shot)", "0:50 (1:00-1:50)", [
        ("1:00", "ALI",
         "Chrome: Submit form. Click the message box and TYPE SLOWLY: "
         "Water main burst flooding the street near the school. Then set Location to: "
         "Block 4, Street 12. Click Submit. Wait for the result card.",
         "I'm submitting a real complaint. One call goes to the backend, which sends it "
         "to Groq's LLM to classify it.",
         []),
        ("1:20", "ASHAR",
         "Result card must stay on screen. Point at Category, Priority, the triaged-by "
         "line, and the AI summary. Do not scroll away.",
         "It comes back as a water issue, high priority, routed to the water "
         "department. And notice the summary - the LLM rewrote my sentence into one "
         "line. That's the live model.",
         []),
        ("1:40", "ALI",
         "Stay on the result card. Point at the latency number if it is visible.",
         "Triage took one point four seconds.",
         []),
    ]),
    ("BEAT 4 - FALLBACK WHEN THE AI IS DOWN", "0:35 (1:50-2:25)", [
        ("1:50", "ALI",
         "Alt+Tab to the terminal. Paste C06 then C07. Wait until the backend reports "
         "healthy again (about 20 seconds).",
         "What happens when the AI is down? Nothing breaks. The triage layer is a chain "
         "- LLM, then Ollama, then rules, then a simulated provider. I'm forcing the "
         "fallback now.",
         ["C06", "C07"]),
        ("2:05", "ALI",
         "Paste C08 from the txt file. Do NOT press the Up arrow - the last command "
         "was the container restart, not the POST. Point at the JSON. "
         "It must show triaged_by: simulated.",
         "Same request, HTTP 201, still categorised as water - but triaged-by says "
         "simulated, and latency drops to one millisecond. The citizen never sees an "
         "error. It's all documented in docs/TRIAGE.md.",
         ["C08"]),
    ]),
    ("BEAT 5 - NETWORK ISOLATION", "0:30 (2:25-2:55)", [
        ("2:25", "ASHAR",
         "Terminal: paste C09. Point at the Ports column - only frontend and backend "
         "have host ports.",
         "Only the web tier is published - look at the ports column. Postgres and Redis "
         "have no host port at all.",
         ["C09"]),
        ("2:38", "ASHAR",
         "Paste C10 then C11. Both must print 000.",
         "From the host, both refuse the connection. The data stores are fully isolated; "
         "the app reaches them over an internal Docker network only.",
         ["C10", "C11"]),
    ]),
    ("BEAT 6 - HPA SCALING ON KUBERNETES", "1:00 (2:55-3:55)", [
        ("2:55", "ALI",
         "Terminal: paste C12, then C13. Point at the running pods.",
         "Same application, now on Kubernetes. I'm running a load test with k6 while we "
         "watch the autoscaler.",
         ["C12", "C13"]),
        ("3:05", "ASHAR",
         "Split the screen: TERMINAL A gets C14 and is left running. TERMINAL B gets "
         "C15. Point at CPU climbing and the replica count going 2 -> 3.",
         "The HPA targets sixty percent CPU, minimum two pods, maximum ten. Watch - CPU "
         "climbs from one percent to ninety, and replicas go from two to three.",
         ["C14", "C15"]),
        ("3:40", "ALI",
         "Flash docs/evidence/18-hpa-load-chart.png for 3 seconds, then back to the "
         "terminal. Ctrl+C to stop k6 and the hpa watch.",
         "When the load stops, it scales back down. This is the measured chart from our "
         "evidence file.",
         []),
    ]),
    ("BEAT 7 - ROLLBACK", "0:40 (3:55-4:35)", [
        ("3:55", "ALI",
         "Terminal: paste C16, then C17, then C18. The restart is what creates the "
         "revision history - without it the undo fails.",
         "Deployments are immutable, so rollback is one command. First I create a new "
         "revision, then I undo it - and it rolls back to the previous one.",
         ["C16", "C17", "C18"]),
        ("4:15", "ALI",
         "Paste C19, C20, C21. A 'last-applied-configuration' Warning is EXPECTED - "
         "ignore it. C21 must print still-serving:200.",
         "The app never stopped serving - HTTP 200 straight after. In production this is "
         "our release safety net, and it's written down in the runbook.",
         ["C19", "C20", "C21"]),
    ]),
    ("BEAT 8 - CLOSE", "0:15 (4:35-4:50)", [
        ("4:35", "ALI",
         "Camera on both faces. No terminal.",
         "What we'd ship next: real SMS and email notifications to the departments.",
         []),
        ("4:42", "ASHAR",
         "Camera on both faces. No terminal.",
         "And a public analytics dashboard for city-wide trends.",
         []),
    ]),
]

# --------------------------------------------------------------------- docx --
def build_docx() -> None:
    doc = Document()

    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = Inches(11), Inches(8.5)
    for attr, val in (("left_margin", 0.5), ("right_margin", 0.5),
                      ("top_margin", 0.5), ("bottom_margin", 0.5)):
        setattr(sec, attr, Inches(val))

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)

    h = doc.add_heading("CivicPulse - J4 Video Shooting Script", level=0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Total 4:50  |  both voices must be audible  |  both partners on camera")
    r.bold = True

    for line in (
        "ALI (you) drives the keyboard and pastes the commands from "
        "docs/VIDEO-SCRIPT-COMMANDS.txt.",
        "ASHAR reads the 'Exact words to say' column from this document.",
        "The Cmd column gives the command numbers in VIDEO-SCRIPT-COMMANDS.txt - "
        "find the number, copy the line, paste it.",
        "Nothing on this page is a secret. Do NOT show the contents of .env on camera.",
    ):
        doc.add_paragraph(line, style="List Bullet")

    widths = [Inches(0.55), Inches(0.55), Inches(2.85), Inches(4.35), Inches(0.75)]

    for title, duration, rows in BEATS:
        doc.add_heading(f"{title}   [{duration}]", level=1)
        table = doc.add_table(rows=1, cols=5)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        for cell, label, w in zip(table.rows[0].cells,
                                  ("Time", "Who", "What to do on screen",
                                   "Exact words to say", "Cmd"),
                                  widths):
            cell.text = ""
            run = cell.paragraphs[0].add_run(label)
            run.bold = True
            cell.width = w

        for time, who, screen, words, cmds in rows:
            cells = table.add_row().cells
            for cell, value, w in zip(cells, (time, who, screen, words, ""), widths):
                cell.text = ""
                para = cell.paragraphs[0]
                run = para.add_run(value)
                run.font.size = Pt(10)
                if value in ("ALI", "ASHAR"):
                    run.bold = True
                cell.width = w
            cells[4].text = " ".join(cmds) if cmds else "-"

        doc.add_paragraph()

    # command appendix
    doc.add_heading("Appendix - every command, in one place", level=1)
    ap = doc.add_table(rows=1, cols=3)
    ap.style = "Table Grid"
    ap.autofit = False
    ap_w = [Inches(0.6), Inches(6.6), Inches(3.05)]
    for cell, label, w in zip(ap.rows[0].cells, ("Cmd", "Command", "Note / expected output"), ap_w):
        cell.text = ""
        run = cell.paragraphs[0].add_run(label)
        run.bold = True
        cell.width = w
    for cid, (cmd, note) in COMMANDS.items():
        cells = ap.add_row().cells
        for cell, value, w, mono in ((cells[0], cid, ap_w[0], False),
                                     (cells[1], cmd, ap_w[1], True),
                                     (cells[2], note, ap_w[2], False)):
            cell.text = ""
            run = cell.paragraphs[0].add_run(value)
            run.font.size = Pt(9)
            if mono:
                run.font.name = "Consolas"
            cell.width = w

    DOCX_OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(DOCX_OUT)


# ---------------------------------------------------------------------- txt --
def build_txt() -> None:
    out: list[str] = []
    rule = "=" * 78
    out.append(rule)
    out.append("CIVICPULSE - J4 VIDEO COMMANDS (copy / paste during the recording)")
    out.append(rule)
    out.append("")
    out.append("Companion to  docs/VIDEO-SCRIPT-J4.docx  - the Cmd column there")
    out.append("refers to the C-numbers below.")
    out.append("")
    out.append("  PRE-FLIGHT  = run once, before you hit record  (P01-P04)")
    out.append("  RECORDING   = during the video                   (C01-C21)")
    out.append("  AFTER       = after you stop recording            (A01-A02)")
    out.append("")
    out.append("Timing map:  B1 clone | B2 compose up | B3 AI triage | B4 fallback")
    out.append("             B5 isolation | B6 HPA | B7 rollback | B8 close")
    out.append("")
    out.append("RULES")
    out.append("  * Never show the inside of .env on camera.")
    out.append("  * Never show the API key.")
    out.append("  * Paste ONE command at a time, then wait for it to finish.")
    out.append("")
    out.append(rule)
    out.append("PRE-FLIGHT  -  run these ONCE before recording. Do not record this part.")
    out.append(rule)
    out.append("")
    for cid in ("P01", "P02", "P03", "P04"):
        cmd, note = COMMANDS[cid]
        out.append(f"{cid}  {note}")
        out.append(cmd)
        out.append("")

    out.append(rule)
    out.append("RECORDING  -  beat by beat")
    out.append(rule)
    out.append("")
    for title, duration, rows in BEATS:
        out.append(f"### {title}   [{duration}]")
        out.append("")
        for time, who, _screen, _words, cmds in rows:
            out.append(f"  [{time}]  {who}")
            for cid in cmds:
                cmd, note = COMMANDS[cid]
                out.append(f"      {cid}  {note}")
                out.append(f"          {cmd}")
            if not cmds:
                out.append("      (no command - screen action only)")
            out.append("")
        out.append("")

    out.append(rule)
    out.append("AFTER RECORDING  -  restore the machine")
    out.append(rule)
    out.append("")
    for cid in ("A01", "A02"):
        cmd, note = COMMANDS[cid]
        out.append(f"{cid}  {note}")
        out.append(cmd)
        out.append("")

    TXT_OUT.parent.mkdir(parents=True, exist_ok=True)
    TXT_OUT.write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_docx()
    build_txt()
    print(f"wrote {DOCX_OUT}")
    print(f"wrote {TXT_OUT}")
