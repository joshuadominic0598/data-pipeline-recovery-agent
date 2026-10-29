"""Render editable SVG service/production diagrams; export PNG with librsvg."""

import html
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/diagrams"

class Canvas:
    def __init__(self, palette, width=1920, height=1240):
        self.p = palette
        self.width, self.height = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            "<style>text{font-family:Arial,Helvetica,sans-serif} .arrow{fill:none;stroke-linecap:round;stroke-linejoin:round}</style>",
            "<defs>",
        ]
        for name in ["accent", "secondary", "muted"]:
            color = palette[name]
            self.parts.append(
                f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10Z" fill="{color}"/></marker>'
            )
        self.parts.append("</defs>")
        self.rect(0, 0, width, height, palette["bg"], palette["bg"], 0)

    def rect(self, x, y, w, h, fill=None, stroke=None, radius=12, dashed=False):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill or self.p["card"]}" stroke="{stroke or self.p["line"]}" stroke-width="1.6"'
            + (' stroke-dasharray="8 6"' if dashed else "")
            + "/>"
        )

    def text(self, x, y, value, size=20, color=None, bold=False, anchor="start"):
        self.parts.append(
            f'<text x="{x}" y="{y}" fill="{color or self.p["ink"]}" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="{anchor}">{html.escape(value)}</text>'
        )

    def arrow(self, points, color="accent", label=None, label_at=None, dashed=False):
        self.parts.append(
            f'<polyline class="arrow" points="{" ".join(f"{x},{y}" for x, y in points)}" stroke="{self.p[color]}" stroke-width="2.4" marker-end="url(#{color})"'
            + (' stroke-dasharray="8 6"' if dashed else "")
            + "/>"
        )
        if label:
            self.text(*label_at, label, 15, self.p[color], anchor="middle")

    def icon(self, x, y, kind, color=None):
        paths = {
            "data": "M3 6c0-5 18-5 18 0s-18 5-18 0v12c0 5 18 5 18 0V6 M3 12c0 5 18 5 18 0",
            "job": "M3 3h7v7H3Z M14 14h7v7h-7Z M10 6h7v8 M6 10v7h8",
            "code": "M8 5L2 12l6 7 M16 5l6 7-6 7 M14 3l-4 18",
            "agent": "M5 6h14v13H5Z M12 2v4 M8 11h1 M15 11h1 M8 16h8 M2 10v5 M22 10v5",
            "check": "M4 3h16v18H4Z M7 12l4 4 6-8",
            "user": "M8 7a4 4 0 1 0 8 0 4 4 0 0 0-8 0 M4 22v-5c0-5 16-5 16 0v5Z",
            "model": "M12 2l9 5v10l-9 5-9-5V7Z M3 7l9 5 9-5 M12 12v10",
            "release": "M3 8l9-5 9 5-9 5Z M3 8v10l9 5 9-5V8 M12 13v10",
            "mail": "M2 5h20v14H2Z M2 5l10 8L22 5",
            "trace": "M3 21V3 M3 21h19 M6 15l5-7 4 4 6-8",
        }
        self.parts.append(
            f'<svg x="{x}" y="{y}" width="30" height="30" viewBox="0 0 24 24"><path d="{paths[kind]}" fill="none" stroke="{color or self.p["accent"]}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        )

    def card(self, x, y, w, h, title, lines, kind="job", accent=False, title_size=23):
        self.rect(x, y, w, h, stroke=self.p["accent"] if accent else None)
        self.icon(x + 20, y + 22, kind)
        self.text(x + 64, y + 45, title, title_size, bold=True)
        for i, line in enumerate(lines):
            self.text(x + 21, y + 83 + i * 27, line, 18, self.p["text"])

    def lane(self, y, h, label):
        self.rect(40, y, 1840, h, self.p["group"], self.p["line"], 15)
        self.text(64, y + 32, label, 17, self.p["accent"], True)

    def save(self, name):
        self.parts.append("</svg>")
        path = OUT / f"{name}.svg"
        path.write_text("\n".join(self.parts) + "\n")
        converter = shutil.which("rsvg-convert") or "/opt/homebrew/bin/rsvg-convert"
        subprocess.run(
            [converter, "-w", str(self.width), "-o", str(OUT / f"{name}.png"), str(path)], check=True
        )

def system_view():
    c = Canvas(
        {
            "bg": "#FFF9F1",
            "group": "#F7EDE0",
            "card": "#FFFDFA",
            "line": "#D8C3AC",
            "ink": "#352B28",
            "text": "#6A554A",
            "accent": "#B64E32",
            "secondary": "#9B742D",
            "muted": "#9D897A",
        }
    )
    c.text(64, 52, "SERVICES / TOOLS / RELEASES / EVIDENCE", 16, c.p["accent"], True)
    c.text(64, 108, "VitalRoute — Recovery system architecture", 42, bold=True)
    c.text(1840, 100, "LOCAL IMPLEMENTATION", 17, c.p["accent"], True, "end")
    c.lane(146, 230, "01  DAILY DATA PLANE")
    c.card(
        64,
        206,
        330,
        132,
        "Hospital logistics",
        ["Daily synthetic shipments", "Optional live weather snapshot"],
        "data",
    )
    c.card(
        526,
        206,
        360,
        132,
        "PySpark pipeline",
        ["Ingest → clean → preprocess", "Domain rules → consumption"],
        "job",
    )
    c.card(
        1018,
        206,
        360,
        132,
        "Parquet checkpoints",
        ["Immutable raw source snapshot", "Stage outputs + quarantine"],
        "data",
    )
    c.card(
        1510,
        206,
        320,
        132,
        "Trusted data product",
        ["Inventory + cold-chain risk", "Reports / APIs / ML features"],
        "check",
        title_size=21,
    )
    for a, b, label in [
        (394, 526, "daily batch"),
        (886, 1018, "checkpoint"),
        (1378, 1510, "verify + publish"),
    ]:
        c.arrow([(a, 272), (b, 272)], label=label, label_at=((a + b) / 2, 255))
    c.text(64, 435, "02  LIVE RECOVERY AGENT & TOOL CALLS", 17, c.p["accent"], True)
    c.card(
        64,
        530,
        170,
        180,
        "Owner",
        ["Trigger a run", "Inspect evidence", "Approve / reject"],
        "user",
        title_size=22,
    )
    c.card(
        314,
        510,
        290,
        220,
        "React console",
        [
            "Pipeline stages + live trace",
            "Tested diff + quality results",
            "Approval and run history",
            "React + TypeScript",
        ],
        "job",
    )
    c.rect(740, 482, 690, 280, stroke=c.p["accent"])
    c.icon(761, 504, "agent")
    c.text(807, 529, "Recovery Agent", 29, bold=True)
    c.text(765, 568, "FastAPI + Python worker · durable recovery state machine", 19, c.p["text"])
    c.text(765, 606, "Inspect → diagnose → propose patch → test → resume → verify", 19, c.p["accent"])
    for x, title, lines in [
        (765, "Diagnostic tools", ["Schema / profiles / manifest", "Code + registry probe"]),
        (987, "Coding tool", ["Reviewed Python patches", "Whole-module AST check"]),
        (1209, "Spark executor", ["Isolated candidate tests", "Checkpoint-based reruns"]),
    ]:
        c.rect(x, 634, 197, 104, c.p["group"])
        c.text(x + 12, 661, title, 18, bold=True)
        for i, line in enumerate(lines):
            c.text(x + 12, 691 + i * 23, line, 14, c.p["text"])
    c.card(
        1550,
        482,
        280,
        280,
        "Investigator mode",
        [
            "Qwen3 8B via Ollama",
            "Local model chooses tools",
            "",
            "Explicit runbook mode",
            "No model required",
        ],
        "model",
        title_size=21,
    )
    c.arrow([(234, 584), (314, 584)], label="control", label_at=(274, 569))
    c.arrow([(314, 660), (234, 660)], label="review", label_at=(274, 684))
    c.arrow([(604, 562), (740, 562)], label="trigger / approve", label_at=(672, 546))
    c.arrow([(740, 693), (604, 693)], label="trace + results", label_at=(672, 715))
    c.arrow([(1430, 553), (1550, 553)], label="request", label_at=(1490, 537))
    c.arrow([(1550, 687), (1430, 687)], label="tool selection", label_at=(1490, 711))
    c.arrow([(706, 338), (706, 405), (903, 405), (903, 482)], label="failure event", label_at=(811, 395))
    c.arrow([(1198, 338), (1198, 482)], label="evidence", label_at=(1244, 416))
    c.lane(866, 296, "03  CONTROL, RELEASE & OBSERVABILITY")
    c.card(
        64,
        924,
        370,
        204,
        "Repair policy",
        [
            "Evidence-eligible runbooks",
            "No arbitrary model code",
            "Sandbox + seven quality gates",
            "Unknown repairs stop",
        ],
        "check",
    )
    c.card(
        530,
        924,
        370,
        204,
        "Approval checkpoint",
        [
            "Required for data / dependency edits",
            "Exact code + input digest",
            "Survives application restart",
            "Rejected changes never deploy",
        ],
        "user",
        title_size=22,
    )
    c.card(
        996,
        924,
        370,
        204,
        "Local Git release",
        [
            "Commit the tested Python patch",
            "Deploy a commit-addressed artifact",
            "Resume the failed stage + dependents",
            "Publish after data checks pass",
        ],
        "release",
        title_size=22,
    )
    c.card(
        1462,
        924,
        370,
        204,
        "State & notifications",
        [
            "SQLite WAL · full agent trace",
            "Diagnosis / latency / tokens / cost",
            "Durable email outbox",
            "Gmail OAuth when configured",
        ],
        "trace",
        title_size=22,
    )
    c.arrow([(434, 1023), (530, 1023)], "secondary")
    c.arrow([(900, 1023), (996, 1023)], "secondary")
    c.arrow([(1366, 1023), (1462, 1023)], "secondary")
    c.arrow(
        [(820, 762), (820, 812), (48, 812), (48, 912), (249, 912), (249, 924)],
        "secondary",
        label="evaluate repair",
        label_at=(465, 801),
    )
    c.arrow(
        [(1181, 924), (1181, 824), (1340, 824), (1340, 762)],
        "secondary",
        label="tested release + resume",
        label_at=(1445, 815),
    )
    c.text(
        64,
        1203,
        "Local releases are real. GitHub push and Databricks promotion are covered in the separate production target view.",
        18,
        c.p["text"],
    )
    c.save("recovery_system")

def production_view():
    c = Canvas(
        {
            "bg": "#F4F7FC",
            "group": "#E8EEF9",
            "card": "#FFFFFF",
            "line": "#BDCBE0",
            "ink": "#172B50",
            "text": "#4D6080",
            "accent": "#285DAB",
            "secondary": "#CB513D",
            "muted": "#8192AF",
        },
        height=1350,
    )
    c.text(64, 52, "DATABRICKS / GITHUB / CONTROLLED PRODUCTION RECOVERY", 16, c.p["accent"], True)
    c.text(64, 108, "From failed job to verified production recovery", 40, bold=True)
    c.text(1840, 100, "PRODUCTION TARGET · NOT DEPLOYED", 16, c.p["secondary"], True, "end")
    c.lane(150, 270, "01  DATABRICKS WORKSPACE — DETECT, INVESTIGATE & TEST")
    top = [
        (
            64,
            "01  Scheduled job",
            [
                "Lakeflow job runs the PySpark stages",
                "Successful tasks save checkpoints",
                "Daily hospital logistics partition",
            ],
            "job",
        ),
        (
            530,
            "02  Task failure",
            ["Capture logs, schema and source version", "Stop dependent stages", "Notify the pipeline owner"],
            "trace",
        ),
        (
            996,
            "03  Hosted recovery agent",
            [
                "Agent runs as a Databricks task",
                "Investigate evidence and propose a diff",
                "Use a configured workspace model*",
            ],
            "agent",
        ),
        (
            1462,
            "04  Isolated candidate",
            [
                "Patch a notebook / .py sandbox copy",
                "Run the candidate on isolated data",
                "Require job AND data-quality tests",
            ],
            "code",
        ),
    ]
    for x, title, lines, icon in top:
        c.card(x, 215, 370, 166, title, lines, icon, title_size=22)
    for a, b in [(434, 530), (900, 996), (1366, 1462)]:
        c.arrow([(a, 296), (b, 296)])
    c.lane(505, 280, "02  GOVERNANCE & SOURCE-CONTROLLED PROMOTION — RIGHT TO LEFT")
    middle = [
        (
            1462,
            "05  Policy + owner review",
            [
                "Auto: reviewed low-risk repair",
                "Owner: data or dependency change",
                "Design change → engineering review",
                "Save exact code / input approval",
            ],
            "user",
        ),
        (
            996,
            "06  GitHub commit / PR",
            [
                "Promotion service commits tested diff",
                "Attach evidence and approval digest",
                "Honor branch protection + reviews",
                "Git is the source of truth",
            ],
            "code",
        ),
        (
            530,
            "07  CI on the exact commit",
            [
                "Repeat tests and quality gates",
                "Reject stale code / input digests",
                "Validate the Databricks bundle",
                "Authorize deployment identity",
            ],
            "check",
        ),
        (
            64,
            "08  Deploy new bundle",
            [
                "Deploy the approved source revision",
                "Update notebook / .py and job assets",
                "Record release + commit identifiers",
                "Do not edit a running job in place",
            ],
            "release",
        ),
    ]
    for x, title, lines, icon in middle:
        c.card(x, 570, 370, 193, title, lines, icon, title_size=21)
    c.arrow([(1647, 381), (1647, 570)], label="tests pass", label_at=(1708, 467))
    for a, b in [(1462, 1366), (996, 900), (530, 434)]:
        c.arrow([(a, 664), (b, 664)], "secondary")
    c.lane(870, 290, "03  REPAIR & VERIFY — AFTER THE ORIGINAL RUN IS TERMINAL")
    c.card(
        64,
        935,
        525,
        192,
        "09  Repair the failed run",
        [
            "Use the updated deployed job settings",
            "Rerun failed tasks and their dependents",
            "Reuse successful upstream checkpoints",
            "Track the new repair attempt",
        ],
        "job",
    )
    c.card(
        684,
        935,
        525,
        192,
        "10  Verify + publish",
        [
            "Check repaired run status and seven data gates",
            "Validate counts, duplicates, freshness and rules",
            "Match results to the approved code + source",
            "Publish only the verified data product",
        ],
        "check",
    )
    c.card(
        1304,
        935,
        525,
        192,
        "11  Notify + close incident",
        [
            "Email the owner: failure, fix and impact",
            "Include commit / release / repair identifiers",
            "Attach validation and trace evidence",
            "Close only after verified recovery",
        ],
        "mail",
    )
    c.arrow(
        [(249, 763), (249, 824), (48, 824), (48, 919), (249, 919), (249, 935)],
        "secondary",
        label="deployed revision",
        label_at=(333, 813),
    )
    c.arrow([(589, 1028), (684, 1028)])
    c.arrow([(1209, 1028), (1304, 1028)])
    c.rect(64, 1194, 1768, 62, "#FFF0EC", "#E4B8AE", 10)
    c.text(
        88,
        1232,
        "Any failed test, rejected approval or bad verification stops promotion/publication and retains the last trusted data.",
        21,
        c.p["secondary"],
        True,
    )
    c.text(
        64,
        1295,
        "* Local demo: Qwen via Ollama. Hosted reference: runbook mode. Workspace model adapter + identity-backed approval/promotion remain integration work.",
        17,
        c.p["text"],
    )
    c.text(
        64,
        1324,
        "Durable production evidence: Delta/control database + immutable data snapshots. Separate agent, reviewer and deployment identities.",
        17,
        c.p["text"],
    )
    c.save("databricks_production")

if __name__ == "__main__":
    dot = shutil.which("dot") or "/opt/homebrew/bin/dot"
    for extension in ["svg", "png"]:
        subprocess.run(
            [
                dot,
                f"-T{extension}",
                str(OUT / "architecture.dot"),
                "-o",
                str(OUT / f"architecture.{extension}"),
            ],
            check=True,
        )
    system_view()
    production_view()
