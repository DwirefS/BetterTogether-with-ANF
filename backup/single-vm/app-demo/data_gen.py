"""
AlphaAgent — Synthetic FSI Data Generator
Creates realistic capital markets documents for the demo:
  - SEC 10-K/10-Q style research PDFs
  - Risk & compliance briefs
  - Key financial metrics XLSX spreadsheets
  - Trade surveillance policy document
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from openpyxl import Workbook


@dataclass(frozen=True)
class SyntheticCompany:
    ticker: str
    name: str
    sector: str
    revenue_ttm: float
    ebitda_ttm: float
    eps: float
    net_debt_ebitda: float
    var_99: float
    liquidity: float
    capex: float
    capex_prior: float


COMPANIES: List[SyntheticCompany] = [
    SyntheticCompany(
        "ALPH", "Alpha Markets Infrastructure Inc.", "Market Infrastructure",
        revenue_ttm=12.4, ebitda_ttm=3.1, eps=5.42, net_debt_ebitda=1.8,
        var_99=18.6, liquidity=2.7, capex=1.85, capex_prior=1.42,
    ),
    SyntheticCompany(
        "BETA", "Beta Quant Strategies LLC", "Hedge Fund / Systematic Trading",
        revenue_ttm=8.7, ebitda_ttm=2.4, eps=3.18, net_debt_ebitda=0.9,
        var_99=32.1, liquidity=4.2, capex=0.95, capex_prior=0.71,
    ),
    SyntheticCompany(
        "GAMM", "Gamma Payments & Clearing Co.", "Payments / Clearing",
        revenue_ttm=21.3, ebitda_ttm=6.8, eps=8.95, net_debt_ebitda=2.1,
        var_99=12.4, liquidity=5.8, capex=3.20, capex_prior=2.65,
    ),
]


def _wrap_text(text: str, max_chars: int) -> List[str]:
    """Word-wrap text to fit within max_chars per line."""
    words = text.split()
    lines: List[str] = []
    cur: List[str] = []
    n = 0
    for w in words:
        if n + len(w) + (1 if cur else 0) > max_chars:
            lines.append(" ".join(cur))
            cur = [w]
            n = len(w)
        else:
            cur.append(w)
            n += len(w) + (1 if len(cur) > 1 else 0)
    if cur:
        lines.append(" ".join(cur))
    return lines


def _write_pdf(path: Path, title: str, paragraphs: List[str]) -> None:
    """Generate a multi-page PDF from a title and list of paragraphs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    y = height - 72

    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, title)
    y -= 24

    c.setFont("Helvetica", 10)
    for p in paragraphs:
        for line in _wrap_text(p, 95):
            if y < 72:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - 72
            c.drawString(72, y, line)
            y -= 14
        y -= 8
    c.save()


def _write_xlsx(path: Path, company: SyntheticCompany) -> None:
    """Generate an XLSX spreadsheet with key financial metrics."""
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Key Metrics"

    ws.append(["Ticker", company.ticker])
    ws.append(["Company", company.name])
    ws.append(["Sector", company.sector])
    ws.append(["AsOf", str(date.today())])
    ws.append([])
    ws.append(["Metric", "Value", "Unit", "Notes"])

    rows = [
        ("Revenue_TTM", company.revenue_ttm, "USD_B", "Trailing twelve months revenue (synthetic)"),
        ("EBITDA_TTM", company.ebitda_ttm, "USD_B", "Trailing twelve months EBITDA (synthetic)"),
        ("EBITDA_Margin", round(company.ebitda_ttm / company.revenue_ttm * 100, 1), "%", "EBITDA / Revenue (synthetic)"),
        ("EPS_FY2025", company.eps, "USD", "FY2025 earnings per share (synthetic)"),
        ("NetDebt_to_EBITDA", company.net_debt_ebitda, "x", "Leverage proxy (synthetic)"),
        ("VaR_99_1d", company.var_99, "USD_M", "Trading VaR 99% 1-day (synthetic)"),
        ("Liquidity_Buffer", company.liquidity, "USD_B", "High quality liquid assets (synthetic)"),
        ("CapEx_Current", company.capex, "USD_B", "Current period capital expenditure (synthetic)"),
        ("CapEx_Prior", company.capex_prior, "USD_B", "Prior period capital expenditure (synthetic)"),
        ("CapEx_YoY_Change", round((company.capex - company.capex_prior) / company.capex_prior * 100, 1), "%", "Year-over-year CapEx variance (synthetic)"),
    ]
    for r in rows:
        ws.append(list(r))

    ws2 = wb.create_sheet("Earnings Timeline")
    ws2.append(["Quarter", "Event", "Impact", "Commentary"])
    ws2.append(["Q3 2025", "Earnings beat", "Positive", "Operating leverage improved; costs controlled."])
    ws2.append(["Q4 2025", "Guidance reiterated", "Neutral", "Management maintained FY2026 outlook."])
    ws2.append(["Q1 2026", "Risk disclosure update", "Mixed", "Added language about funding spreads volatility."])

    wb.save(str(path))


def ensure_synthetic_dataset(data_root: str) -> None:
    """
    Generate a complete synthetic FSI dataset on the ANF mount.
    Idempotent: if data_root already has files, skip generation.
    """
    root = Path(data_root)
    root.mkdir(parents=True, exist_ok=True)

    # Idempotent check
    if any(p.is_file() for p in root.rglob("*")):
        print(f"  Synthetic data already exists at {root}, skipping generation.")
        return

    print(f"  Generating synthetic FSI dataset at {root} ...")

    for c in COMPANIES:
        # SEC 10-K style research note
        _write_pdf(
            root / "research" / f"{c.ticker}_SellSide_Research_Note.pdf",
            title=f"{c.name} ({c.ticker}) — Synthetic Sell-Side Research Note",
            paragraphs=[
                "DISCLAIMER: This is synthetic demo content generated for an Azure + NVIDIA + Azure NetApp Files AI demo. "
                "It does not constitute investment advice and all figures are entirely fictional.",
                f"Company Overview: {c.name} operates in the {c.sector} sector of the capital markets industry. "
                f"The company reported trailing twelve-month revenue of ${c.revenue_ttm}B with EBITDA of ${c.ebitda_ttm}B, "
                f"representing an EBITDA margin of {round(c.ebitda_ttm / c.revenue_ttm * 100, 1)}%. "
                f"Earnings per share for FY2025 came in at ${c.eps}.",
                f"Investment Thesis: {c.name} is positioned to benefit from ongoing modernization across capital markets workflows. "
                "We see upside from automation of trade processing, improved operational resilience through AI-assisted "
                "risk management, and stronger regulatory governance frameworks. The company's investment in data center "
                "infrastructure and GPU-accelerated computing positions it well for the agentic AI transition.",
                f"Capital Expenditure Analysis: Current period CapEx stands at ${c.capex}B, up from ${c.capex_prior}B "
                f"in the prior period, representing a {round((c.capex - c.capex_prior) / c.capex_prior * 100, 1)}% "
                "year-over-year increase. The increase is primarily driven by investments in AI infrastructure, "
                "including NVIDIA GPU clusters for real-time inference and Azure NetApp Files for high-performance "
                "data storage supporting agentic AI workloads.",
                "Key Catalysts: (1) Platform modernization programs accelerating electronic trading volumes, "
                "(2) Productivity uplift through AI-assisted operations reducing manual processing by 40%, "
                "(3) Stronger regulatory alignment enabling faster compliance reporting, and "
                "(4) Strategic partnership with cloud and AI infrastructure providers.",
                "Key Risks: (1) Funding spread volatility impacting net interest margin, "
                "(2) Model risk and AI governance gaps requiring additional investment, "
                "(3) Operational incidents and cyber events increasing in frequency and sophistication, "
                "(4) Tightening of capital or liquidity requirements under Basel IV implementation, and "
                "(5) Competitive pressure from fintech challengers with lower cost structures.",
                "Valuation: We maintain our target price based on a 12x forward EBITDA multiple, "
                "which implies approximately 15% upside from current levels. Our DCF model assumes "
                "a 3-year revenue CAGR of 8.5% with gradual margin expansion as AI investments mature.",
                "Questions for Management: How are you measuring operational risk reduction from AI implementations? "
                "What is the target latency for data pipelines supporting agentic AI workloads? "
                "How do you segment sensitive datasets for compliance with SEC Rule 17a-4?",
            ],
        )

        # Risk & compliance brief
        _write_pdf(
            root / "risk" / f"{c.ticker}_Risk_and_Compliance_Brief.pdf",
            title=f"{c.name} ({c.ticker}) — Synthetic Risk & Compliance Brief",
            paragraphs=[
                "DISCLAIMER: Synthetic demo content for an AI + storage technical demonstration. Not a real institution.",
                f"Compliance Status: {c.name} is subject to SEC, FINRA, and applicable international regulatory frameworks. "
                "This brief summarizes the current risk posture and compliance considerations.",
                "Policy Focus Areas: (a) Model risk management (MRM) — all AI models used in trading and risk decisions "
                "must be validated, documented, and subject to periodic review per SR 11-7 guidance. "
                "(b) Data lineage and retention — all financial data must maintain complete lineage from source to output, "
                "with retention policies meeting SEC Rule 17a-4 requirements for 6-year preservation. "
                "(c) Access controls and least privilege — production data environments must enforce role-based access "
                "with quarterly access reviews. (d) Auditability of decision support — all AI-assisted decisions must "
                "produce auditable logs including input data, model version, and confidence scores.",
                "Agentic AI Implications: Multi-step AI workflows present new governance challenges. "
                "Each agent in a multi-agent system must log: tool calls made, retrieved evidence and sources, "
                "intermediate reasoning steps, and final outputs with citations. "
                "Escalation paths are required when risk thresholds are exceeded — for example, when a proposed "
                "trade exceeds VaR limits or when an AI-generated compliance assessment flags potential violations.",
                f"Risk Metrics: Current 99% 1-day VaR stands at ${c.var_99}M. Liquidity buffer is ${c.liquidity}B. "
                f"Net debt-to-EBITDA leverage ratio is {c.net_debt_ebitda}x, which is "
                f"{'within' if c.net_debt_ebitda < 2.5 else 'approaching'} the internal policy limit of 2.5x.",
                "Data Control Recommendations: Unstructured sources (PDF, spreadsheets, emails) often contain sensitive content "
                "including MNPI (Material Non-Public Information). File-level permissions on Azure NetApp Files, "
                "combined with instant snapshots and rapid cloning, support safer experimentation and rollback. "
                "The Object REST API enables AI services to access documents without moving data outside the secure perimeter.",
            ],
        )

        # Key metrics spreadsheet
        _write_xlsx(root / "spreadsheets" / f"{c.ticker}_Key_Metrics.xlsx", c)

    # Trade surveillance policy (shared across all companies)
    _write_pdf(
        root / "policies" / "Trade_Surveillance_Policy_2026.pdf",
        title="Synthetic Trade Surveillance Policy — Capital Markets Division (2026)",
        paragraphs=[
            "DISCLAIMER: Synthetic demo content for AI + storage technical demonstration.",
            "1. PURPOSE: This policy establishes requirements for automated trade surveillance "
            "within the capital markets division. All electronic trading activity must be monitored "
            "for potential market manipulation, insider trading, and regulatory violations.",
            "2. SCOPE: Applies to all trading desks, algorithmic trading systems, and AI-assisted "
            "order routing systems across equity, fixed income, and derivatives markets.",
            "3. SURVEILLANCE REQUIREMENTS: The surveillance team reviews alerts for spoofing, layering, "
            "wash trades, and front-running. Alerts are prioritized based on severity (1-5), venue, "
            "and trader history. All escalation decisions must be documented with supporting evidence.",
            "4. AI AGENT USAGE POLICY: AI agents used in trading support must operate within defined guardrails. "
            "Maximum position size recommendations from AI agents require human approval above $10M notional. "
            "AI-generated compliance assessments must be reviewed by a licensed compliance officer before "
            "being submitted to regulators. Year-over-year capital expenditure changes exceeding 40% "
            "require additional management review and board notification.",
            "5. DATA RETENTION: The system must support retention of alert context, including chat logs, "
            "supporting documents, market data snapshots, and AI reasoning traces. Minimum retention "
            "period is 6 years per SEC Rule 17a-4. All data must be stored on tamper-evident storage "
            "with cryptographic integrity verification.",
            "6. INCIDENT RESPONSE: Any suspected market manipulation or compliance breach must be reported "
            "to the Chief Compliance Officer within 4 hours. AI systems that detect anomalous patterns "
            "must generate structured incident reports including: timestamp, affected instruments, "
            "estimated market impact, and recommended remediation actions.",
        ],
    )

    total_files = sum(1 for _ in root.rglob("*") if _.is_file())
    print(f"  ✅ Generated {total_files} synthetic files across {len(COMPANIES)} companies.")
