import { useState, useEffect, useMemo } from "react";

const JOBS_URL = "./data/jobs.json";

const SOURCE_COLORS = {
  LinkedIn: { bg: "#E8F0FE", text: "#1a56db", dot: "#1a56db" },
  Indeed:   { bg: "#FEF3C7", text: "#b45309", dot: "#d97706" },
  Handshake:{ bg: "#ECFDF5", text: "#065f46", dot: "#059669" },
};

const SCORE_COLOR = (s) => {
  if (s >= 80) return { bar: "#10b981", label: "#065f46" };
  if (s >= 60) return { bar: "#3b82f6", label: "#1e40af" };
  if (s >= 40) return { bar: "#f59e0b", label: "#92400e" };
  return { bar: "#ef4444", label: "#991b1b" };
};

function ScoreBar({ score }) {
  const c = SCORE_COLOR(score);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{
        flex: 1, height: 6, background: "#f1f5f9", borderRadius: 99, overflow: "hidden"
      }}>
        <div style={{
          width: `${score}%`, height: "100%",
          background: c.bar, borderRadius: 99,
          transition: "width 0.6s ease"
        }} />
      </div>
      <span style={{
        fontSize: 13, fontWeight: 700, color: c.label, minWidth: 32, textAlign: "right"
      }}>{score}</span>
    </div>
  );
}

function Badge({ children, color }) {
  const c = SOURCE_COLORS[color] || { bg: "#f1f5f9", text: "#475569", dot: "#94a3b8" };
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      padding: "2px 9px", borderRadius: 99,
      background: c.bg, color: c.text,
      fontSize: 11, fontWeight: 600, letterSpacing: "0.02em"
    }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: c.dot }} />
      {children}
    </span>
  );
}

function JobCard({ job, onToggle }) {
  const [expanded, setExpanded] = useState(false);
  const sc = SCORE_COLOR(job.score);

  return (
    <div style={{
      background: "#fff",
      border: job.saved ? "1.5px solid #3b82f6" : "1px solid #e2e8f0",
      borderRadius: 14,
      padding: "18px 20px",
      transition: "box-shadow 0.2s",
      cursor: "pointer",
    }}
    onClick={() => setExpanded(e => !e)}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, flexWrap: "wrap" }}>
            <Badge color={job.source}>{job.source}</Badge>
            {job.remote === true && (
              <span style={{
                fontSize: 11, fontWeight: 600, color: "#6d28d9",
                background: "#ede9fe", padding: "2px 9px", borderRadius: 99
              }}>Remote</span>
            )}
            {job.applied && (
              <span style={{
                fontSize: 11, fontWeight: 600, color: "#fff",
                background: "#10b981", padding: "2px 9px", borderRadius: 99
              }}>✓ Applied</span>
            )}
          </div>
          <h3 style={{
            margin: 0, fontSize: 15, fontWeight: 700,
            color: "#0f172a", lineHeight: 1.3,
            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis"
          }}>{job.title}</h3>
          <p style={{ margin: "2px 0 0", fontSize: 13, color: "#64748b" }}>{job.company}</p>
        </div>
        <div style={{ minWidth: 90 }}>
          <div style={{ fontSize: 10, color: "#94a3b8", marginBottom: 4, textAlign: "right" }}>MATCH</div>
          <ScoreBar score={job.score} />
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 14, borderTop: "1px solid #f1f5f9", paddingTop: 14 }}>
          {job.match_reasons?.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#10b981", marginBottom: 5, letterSpacing: "0.05em" }}>WHY IT FITS</div>
              {job.match_reasons.map((r, i) => (
                <div key={i} style={{ fontSize: 13, color: "#374151", display: "flex", gap: 6, marginBottom: 3 }}>
                  <span style={{ color: "#10b981" }}>↗</span> {r}
                </div>
              ))}
            </div>
          )}
          {job.gaps?.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#f59e0b", marginBottom: 5, letterSpacing: "0.05em" }}>GAPS</div>
              {job.gaps.map((g, i) => (
                <div key={i} style={{ fontSize: 13, color: "#374151", display: "flex", gap: 6, marginBottom: 3 }}>
                  <span style={{ color: "#f59e0b" }}>△</span> {g}
                </div>
              ))}
            </div>
          )}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <a
              href={job.url} target="_blank" rel="noreferrer"
              onClick={e => e.stopPropagation()}
              style={{
                padding: "7px 16px", borderRadius: 8, fontSize: 13, fontWeight: 600,
                background: "#0f172a", color: "#fff", textDecoration: "none",
                display: "inline-flex", alignItems: "center", gap: 6
              }}
            >Apply ↗</a>
            <button
              onClick={e => { e.stopPropagation(); onToggle(job.id, "applied"); }}
              style={{
                padding: "7px 14px", borderRadius: 8, fontSize: 13, fontWeight: 600,
                background: job.applied ? "#dcfce7" : "#f8fafc",
                color: job.applied ? "#166534" : "#475569",
                border: "1px solid #e2e8f0", cursor: "pointer"
              }}
            >{job.applied ? "✓ Applied" : "Mark Applied"}</button>
            <button
              onClick={e => { e.stopPropagation(); onToggle(job.id, "saved"); }}
              style={{
                padding: "7px 14px", borderRadius: 8, fontSize: 13, fontWeight: 600,
                background: job.saved ? "#eff6ff" : "#f8fafc",
                color: job.saved ? "#1d4ed8" : "#475569",
                border: "1px solid #e2e8f0", cursor: "pointer"
              }}
            >{job.saved ? "★ Saved" : "☆ Save"}</button>
          </div>
          <div style={{ marginTop: 8, fontSize: 11, color: "#cbd5e1" }}>
            Scraped {new Date(job.scraped_at).toLocaleDateString()}
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [filter, setFilter] = useState("all");
  const [source, setSource] = useState("all");
  const [minScore, setMinScore] = useState(0);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("score");

  useEffect(() => {
    fetch(JOBS_URL)
      .then(r => r.json())
      .then(d => {
        setData(d);
        // Merge with localStorage state (applied/saved flags)
        const saved = JSON.parse(localStorage.getItem("job_states") || "{}");
        const merged = (d.jobs || []).map(j => ({
          ...j,
          applied: saved[j.id]?.applied ?? j.applied,
          saved: saved[j.id]?.saved ?? j.saved,
        }));
        setJobs(merged);
      })
      .catch(() => setData({ jobs: [], meta: { total: 0, new_today: 0 } }));
  }, []);

  const toggle = (id, field) => {
    setJobs(prev => {
      const next = prev.map(j => j.id === id ? { ...j, [field]: !j[field] } : j);
      const states = {};
      next.forEach(j => { states[j.id] = { applied: j.applied, saved: j.saved }; });
      localStorage.setItem("job_states", JSON.stringify(states));
      return next;
    });
  };

  const filtered = useMemo(() => {
    let list = jobs.filter(j => {
      if (filter === "saved" && !j.saved) return false;
      if (filter === "applied" && !j.applied) return false;
      if (filter === "new" && j.applied) return false;
      if (source !== "all" && j.source !== source) return false;
      if (j.score < minScore) return false;
      if (search) {
        const q = search.toLowerCase();
        if (!j.title.toLowerCase().includes(q) && !j.company.toLowerCase().includes(q)) return false;
      }
      return true;
    });
    if (sortBy === "score") list.sort((a, b) => b.score - a.score);
    if (sortBy === "date") list.sort((a, b) => new Date(b.scraped_at) - new Date(a.scraped_at));
    if (sortBy === "company") list.sort((a, b) => a.company.localeCompare(b.company));
    return list;
  }, [jobs, filter, source, minScore, search, sortBy]);

  const stats = useMemo(() => ({
    total: jobs.length,
    high: jobs.filter(j => j.score >= 75).length,
    applied: jobs.filter(j => j.applied).length,
    saved: jobs.filter(j => j.saved).length,
    new: data?.meta?.new_today ?? 0,
  }), [jobs, data]);

  const StatCard = ({ label, value, color }) => (
    <div style={{
      background: "#fff", borderRadius: 12, padding: "14px 18px",
      border: "1px solid #e2e8f0", textAlign: "center"
    }}>
      <div style={{ fontSize: 26, fontWeight: 800, color: color || "#0f172a" }}>{value}</div>
      <div style={{ fontSize: 11, color: "#94a3b8", fontWeight: 600, marginTop: 2, letterSpacing: "0.04em" }}>{label}</div>
    </div>
  );

  return (
    <div style={{
      minHeight: "100vh", background: "#f8fafc",
      fontFamily: "'DM Sans', system-ui, sans-serif",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{
        background: "#0f172a", color: "#fff",
        padding: "24px 32px", position: "sticky", top: 0, zIndex: 10
      }}>
        <div style={{ maxWidth: 900, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 800, letterSpacing: "-0.02em" }}>
              ⚡ Job Hunt Dashboard
            </h1>
            <p style={{ margin: "2px 0 0", fontSize: 12, color: "#94a3b8" }}>
              Charan Somalaraju · {data?.last_updated
                ? `Last run ${new Date(data.last_updated).toLocaleString()}`
                : "No data yet — trigger the workflow"}
            </p>
          </div>
          <div style={{
            background: "#1e293b", borderRadius: 8, padding: "6px 14px",
            fontSize: 12, color: "#38bdf8", fontWeight: 600
          }}>
            {stats.new} new today
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 900, margin: "0 auto", padding: "24px 16px" }}>
        {/* Stats row */}
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
          gap: 12, marginBottom: 24
        }}>
          <StatCard label="TOTAL JOBS" value={stats.total} />
          <StatCard label="STRONG MATCH ≥75" value={stats.high} color="#10b981" />
          <StatCard label="APPLIED" value={stats.applied} color="#3b82f6" />
          <StatCard label="SAVED" value={stats.saved} color="#8b5cf6" />
        </div>

        {/* Filters */}
        <div style={{
          background: "#fff", borderRadius: 14, border: "1px solid #e2e8f0",
          padding: "16px 20px", marginBottom: 20
        }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <input
              type="text"
              placeholder="Search title or company..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{
                flex: "1 1 200px", padding: "8px 14px", borderRadius: 8,
                border: "1px solid #e2e8f0", fontSize: 13, outline: "none",
                fontFamily: "inherit"
              }}
            />
            <select value={filter} onChange={e => setFilter(e.target.value)}
              style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13, fontFamily: "inherit" }}>
              <option value="all">All jobs</option>
              <option value="new">Not applied</option>
              <option value="saved">Saved</option>
              <option value="applied">Applied</option>
            </select>
            <select value={source} onChange={e => setSource(e.target.value)}
              style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13, fontFamily: "inherit" }}>
              <option value="all">All sources</option>
              <option value="LinkedIn">LinkedIn</option>
              <option value="Indeed">Indeed</option>
              <option value="Handshake">Handshake</option>
            </select>
            <select value={sortBy} onChange={e => setSortBy(e.target.value)}
              style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13, fontFamily: "inherit" }}>
              <option value="score">Sort: Best match</option>
              <option value="date">Sort: Newest</option>
              <option value="company">Sort: Company</option>
            </select>
          </div>
          <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 12, color: "#64748b", fontWeight: 500 }}>Min score:</span>
            <input type="range" min="0" max="90" step="5" value={minScore}
              onChange={e => setMinScore(+e.target.value)}
              style={{ flex: 1, maxWidth: 200 }} />
            <span style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", minWidth: 28 }}>{minScore}</span>
            <span style={{ fontSize: 12, color: "#94a3b8" }}>
              Showing {filtered.length} job{filtered.length !== 1 ? "s" : ""}
            </span>
          </div>
        </div>

        {/* Job list */}
        {filtered.length === 0 ? (
          <div style={{
            background: "#fff", borderRadius: 14, border: "1px solid #e2e8f0",
            padding: "60px 20px", textAlign: "center"
          }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
            <h3 style={{ margin: 0, color: "#0f172a" }}>No jobs found</h3>
            <p style={{ color: "#94a3b8", fontSize: 14, margin: "8px 0 0" }}>
              {jobs.length === 0
                ? "Go to your GitHub repo → Actions → Daily Job Hunt → Run workflow"
                : "Try adjusting filters or lowering the minimum score"}
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {filtered.map(job => (
              <JobCard key={job.id} job={job} onToggle={toggle} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
