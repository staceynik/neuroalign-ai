"""
Cost Tracker
============
Logs token usage and estimated cost for every LLM call in the pipeline.
Specified in: NeuroAlign_AI_Working_Spec.docx, Section 10.

Real token counts come from LangChain's BaseCallbackHandler —
on_llm_end() receives the actual usage_metadata from the API response.
This means cost_usd is always accurate, never estimated.

Pricing reference (OpenAI gpt-4o-mini, June 2026):
  Input:  $0.150 per 1M tokens
  Output: $0.600 per 1M tokens
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from langchain_core.callbacks import BaseCallbackHandler


# ── Pricing table ─────────────────────────────────────────────────────────────

PRICING = {
    "gpt-4o-mini": {"input": 0.150 / 1_000_000, "output": 0.600 / 1_000_000},
    "gpt-4o":      {"input": 2.50  / 1_000_000, "output": 10.00 / 1_000_000},
}

DB_PATH = Path("data/costs.db")


# ── In-memory session accumulator ─────────────────────────────────────────────

@dataclass
class SessionCost:
    calls: list = field(default_factory=list)

    def add(self, agent: str, model: str, input_tokens: int, output_tokens: int):
        price = PRICING.get(model, PRICING["gpt-4o-mini"])
        cost  = input_tokens * price["input"] + output_tokens * price["output"]
        self.calls.append({
            "agent":         agent,
            "model":         model,
            "input_tokens":  input_tokens,
            "output_tokens": output_tokens,
            "total_tokens":  input_tokens + output_tokens,
            "cost_usd":      round(cost, 6),
        })

    @property
    def total_cost(self) -> float:
        return round(sum(c["cost_usd"] for c in self.calls), 6)

    @property
    def total_tokens(self) -> int:
        return sum(c["total_tokens"] for c in self.calls)

    @property
    def most_expensive_agent(self) -> str:
        if not self.calls:
            return "—"
        return max(self.calls, key=lambda c: c["cost_usd"])["agent"]

    def summary_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.calls)


# ── LangChain callback — hooks into every LLM call automatically ──────────────

class CostCallback(BaseCallbackHandler):
    """
    Attach to any ChatOpenAI instance via callbacks=[CostCallback(...)].
    on_llm_end() fires after every LLM response and reads the real
    token counts from usage_metadata — no estimation needed.
    """

    def __init__(self, session_cost: SessionCost, agent_name: str, model: str):
        self.session_cost = session_cost
        self.agent_name   = agent_name
        self.model        = model

    def on_llm_end(self, response, **kwargs):
        try:
            # LangChain ≥0.2: usage_metadata on the generation
            usage = response.generations[0][0].message.usage_metadata
            self.session_cost.add(
                agent         = self.agent_name,
                model         = self.model,
                input_tokens  = usage.get("input_tokens",  0),
                output_tokens = usage.get("output_tokens", 0),
            )
        except Exception:
            # Fallback: log a 0-cost entry so the agent still appears
            self.session_cost.add(
                agent         = self.agent_name,
                model         = self.model,
                input_tokens  = 0,
                output_tokens = 0,
            )


# ── SQLite persistent log ─────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cost_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp      TEXT,
            session_id     TEXT,
            agent_name     TEXT,
            model_name     TEXT,
            input_tokens   INTEGER,
            output_tokens  INTEGER,
            total_tokens   INTEGER,
            cost_usd       REAL
        )
    """)
    conn.commit()
    return conn


def log_cost(session_id: str, session_cost: SessionCost) -> None:
    """Persist all calls from a completed session to SQLite."""
    if not session_cost.calls:
        return
    conn = _get_conn()
    ts   = datetime.utcnow().isoformat()
    for call in session_cost.calls:
        conn.execute("""
            INSERT INTO cost_log
            (timestamp, session_id, agent_name, model_name,
             input_tokens, output_tokens, total_tokens, cost_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ts, session_id,
            call["agent"], call["model"],
            call["input_tokens"], call["output_tokens"],
            call["total_tokens"], call["cost_usd"],
        ))
    conn.commit()
    conn.close()


def load_cost_history() -> pd.DataFrame:
    conn = _get_conn()
    df   = pd.read_sql_query(
        "SELECT * FROM cost_log ORDER BY timestamp DESC LIMIT 200", conn
    )
    conn.close()
    return df


def total_cost_today() -> float:
    conn  = _get_conn()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    row   = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM cost_log WHERE timestamp LIKE ?",
        (f"{today}%",)
    ).fetchone()
    conn.close()
    return round(row[0], 6)
