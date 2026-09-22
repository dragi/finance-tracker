import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";

const currency = new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" });

function monthLabel(month) {
  const [year, m] = month.split("-").map(Number);
  return new Date(year, m - 1).toLocaleString(undefined, { month: "long", year: "numeric" });
}

// `refreshKey` changes whenever transactions are added or removed, so the
// report is re-fetched to stay in sync with the list below it.
export default function SpendingChart({ refreshKey }) {
  const [rows, setRows] = useState([]);
  const [month, setMonth] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .get("/reports/monthly")
      .then((data) => {
        if (!cancelled) {
          setRows(data);
          setError("");
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Could not load report");
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  // rows come back newest month first
  const months = [...new Set(rows.map((r) => r.month))];
  const selectedMonth = months.includes(month) ? month : months[0];
  const data = rows
    .filter((r) => r.month === selectedMonth)
    .map((r) => ({ name: r.category_name, total: Number(r.total) }))
    .sort((a, b) => b.total - a.total);
  const monthTotal = data.reduce((sum, d) => sum + d.total, 0);

  return (
    <div className="card">
      <div className="card-header">
        <h2>Spending by category</h2>
        {months.length > 0 && (
          <select value={selectedMonth} onChange={(e) => setMonth(e.target.value)}>
            {months.map((m) => (
              <option key={m} value={m}>
                {monthLabel(m)}
              </option>
            ))}
          </select>
        )}
      </div>
      {error && <p className="form-error">{error}</p>}
      {!error && data.length === 0 ? (
        <p className="muted">Add some transactions to see a report.</p>
      ) : (
        <>
          <p className="muted">Total: {currency.format(monthTotal)}</p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" interval={0} tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={(v) => currency.format(v)} width={80} />
              <Tooltip formatter={(v) => [currency.format(v), "Spent"]} />
              <Bar dataKey="total" fill="#2f6feb" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  );
}
