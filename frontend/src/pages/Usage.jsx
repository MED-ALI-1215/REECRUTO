import { useEffect, useState } from "react";
import { getUsage } from "../api/client";
import { Toast } from "../components/ui";
import { errorMessage, useToast } from "../lib/ui";

const PERIODS = [
  { days: 7, label: "7 days" },
  { days: 30, label: "30 days" },
  { days: 0, label: "All time" },
];

const SERVICE_LABEL = {
  cv_extraction: "CV extraction",
  job_extraction: "Job skills extraction",
  question_generation: "Interview questions",
  answer_scoring: "Answer scoring",
  final_report: "Interview report",
};

const fmt = (n) => new Intl.NumberFormat("en-US").format(n ?? 0);
const usd = (n) => (n >= 0.01 || n === 0 ? `$${(n ?? 0).toFixed(2)}` : `$${n.toFixed(4)}`);

function Tile({ label, value, hint }) {
  return (
    <div className="card" style={{ padding: "16px 18px" }}>
      <p style={{ fontSize: 12, color: "var(--text-dim)", marginBottom: 6 }}>{label}</p>
      <p style={{ fontFamily: "Syne, sans-serif", fontWeight: 800, fontSize: 24 }}>{value}</p>
      {hint && <p style={{ fontSize: 12, color: "var(--text-dim)", marginTop: 4 }}>{hint}</p>}
    </div>
  );
}

// Daily tokens as stacked bars: input (blue) + output (gold)
function DailyChart({ days }) {
  if (days.length === 0) return null;
  const max = Math.max(...days.map(d => d.prompt_tokens + d.completion_tokens), 1);
  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 14, flexWrap: "wrap", gap: 8 }}>
        <p style={{ fontWeight: 600 }}>Tokens per day</p>
        <p style={{ fontSize: 12, color: "var(--text-dim)", display: "flex", gap: 14 }}>
          <span><span style={{ display: "inline-block", width: 10, height: 10, background: "var(--blue)", borderRadius: 2, marginRight: 6 }} />Input</span>
          <span><span style={{ display: "inline-block", width: 10, height: 10, background: "var(--gold)", borderRadius: 2, marginRight: 6 }} />Output</span>
        </p>
      </div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 160, overflowX: "auto" }}>
        {days.map(d => {
          const total = d.prompt_tokens + d.completion_tokens;
          return (
            <div key={d.date} title={`${d.date}\n${fmt(d.prompt_tokens)} in · ${fmt(d.completion_tokens)} out · ${d.calls} calls · ${usd(d.estimated_cost_usd)}`}
              style={{ flex: "1 0 18px", maxWidth: 48, display: "flex", flexDirection: "column", justifyContent: "flex-end", height: "100%" }}>
              <div style={{ height: `${(d.completion_tokens / max) * 100}%`, background: "var(--gold)", borderRadius: "3px 3px 0 0", minHeight: total ? 2 : 0 }} />
              <div style={{ height: `${(d.prompt_tokens / max) * 100}%`, background: "var(--blue)" }} />
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--text-dim)", marginTop: 6 }}>
        <span>{days[0].date}</span>
        <span>{days[days.length - 1].date}</span>
      </div>
    </div>
  );
}

export default function Usage() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [toast, showToast] = useToast();

  useEffect(() => {
    let active = true;
    getUsage(days)
      .then(({ data }) => active && setData(data))
      .catch(err => active && showToast(errorMessage(err, "Could not load usage."), "err"));
    return () => { active = false; };
  }, [days, showToast]);

  const t = data?.totals;
  return (
    <div className="fade-in">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ fontSize: 26, marginBottom: 4 }}>AI Usage</h1>
          <p style={{ color: "var(--text-dim)" }}>Tokens consumed by every LLM call, and the estimated cost.</p>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {PERIODS.map(p => (
            <button key={p.days} onClick={() => setDays(p.days)}
              className={days === p.days ? "btn-primary" : "btn-ghost"} style={{ padding: "8px 14px", fontSize: 13 }}>
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {!data ? (
        <div style={{ display: "flex", justifyContent: "center", paddingTop: 60 }}>
          <span className="spinner" style={{ width: 32, height: 32 }} />
        </div>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 20 }}>
            <Tile label="LLM calls" value={fmt(t.calls)}
              hint={t.failures ? `${t.failures} failed (${Math.round((t.failures / t.calls) * 100)}%)` : "no failures"} />
            <Tile label="Input tokens" value={fmt(t.prompt_tokens)} />
            <Tile label="Output tokens" value={fmt(t.completion_tokens)} hint="includes the model's reasoning" />
            <Tile label="Estimated cost" value={usd(t.estimated_cost_usd)} hint="from the prices in .env" />
          </div>

          <DailyChart days={data.by_day} />

          <div className="card" style={{ padding: 0, overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ color: "var(--text-dim)", textAlign: "right" }}>
                  {["Feature", "Calls", "Input", "Output", "Avg / call", "Cost", "Cost / call", "Avg latency", "Failures"].map((h, i) => (
                    <th key={h} style={{ padding: "12px 14px", fontWeight: 600, textAlign: i === 0 ? "left" : "right", borderBottom: "1px solid var(--border)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.by_service.length === 0 && (
                  <tr><td colSpan={9} style={{ padding: 24, textAlign: "center", color: "var(--text-dim)" }}>No LLM calls in this period.</td></tr>
                )}
                {data.by_service.map(s => (
                  <tr key={s.service} style={{ textAlign: "right", borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "12px 14px", textAlign: "left", fontWeight: 600 }}>{SERVICE_LABEL[s.service] || s.service}</td>
                    <td style={{ padding: "12px 14px" }}>{fmt(s.total_calls)}</td>
                    <td style={{ padding: "12px 14px" }}>{fmt(s.prompt_tokens)}</td>
                    <td style={{ padding: "12px 14px" }}>{fmt(s.completion_tokens)}</td>
                    <td style={{ padding: "12px 14px" }}>{fmt(s.avg_tokens_per_call)}</td>
                    <td style={{ padding: "12px 14px" }}>{usd(s.estimated_cost_usd)}</td>
                    <td style={{ padding: "12px 14px" }}>{usd(s.avg_cost_per_call_usd)}</td>
                    <td style={{ padding: "12px 14px" }}>{fmt(Math.round(s.avg_latency_ms))} ms</td>
                    <td style={{ padding: "12px 14px", color: s.failures ? "var(--red)" : "inherit" }}>{s.failures}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <Toast toast={toast} />
    </div>
  );
}
