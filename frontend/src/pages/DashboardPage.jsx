import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import TransactionForm from "../components/TransactionForm";
import TransactionList from "../components/TransactionList";
import SpendingChart from "../components/SpendingChart";

function byNewest(a, b) {
  if (a.transaction_date !== b.transaction_date) {
    return a.transaction_date < b.transaction_date ? 1 : -1;
  }
  return b.id - a.id;
}

export default function DashboardPage() {
  const { logout } = useAuth();
  const [accounts, setAccounts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [acc, cats, txns] = await Promise.all([
          api.get("/accounts"),
          api.get("/categories"),
          api.get("/transactions"),
        ]);
        setAccounts(acc);
        setCategories(cats);
        setTransactions(txns);
      } catch (err) {
        setError(err.message || "Could not load data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function handleCategoryCreated(category) {
    setCategories((prev) =>
      [...prev, category].sort((a, b) => a.name.localeCompare(b.name))
    );
  }

  function handleCreated(transaction) {
    setTransactions((prev) => [transaction, ...prev].sort(byNewest));
  }

  async function handleDelete(id) {
    setError("");
    try {
      await api.del(`/transactions/${id}`);
      setTransactions((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      setError(err.message || "Could not delete transaction");
    }
  }

  return (
    <div className="dashboard-page">
      <header>
        <h1>Expense Tracker</h1>
        <button onClick={logout}>Sign out</button>
      </header>
      {error && <p className="form-error">{error}</p>}
      {loading ? (
        <p className="muted">Loading...</p>
      ) : (
        <>
          <SpendingChart refreshKey={transactions} />
          <TransactionForm
            accounts={accounts}
            categories={categories}
            onCategoryCreated={handleCategoryCreated}
            onCreated={handleCreated}
          />
          <TransactionList
            transactions={transactions}
            categories={categories}
            onDelete={handleDelete}
          />
        </>
      )}
    </div>
  );
}
