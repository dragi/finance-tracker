import { useAuth } from "../auth/AuthContext";

// Placeholder landing page for now - the transactions list and reports
// chart land in later sprints.
export default function DashboardPage() {
  const { logout } = useAuth();

  return (
    <div className="dashboard-page">
      <header>
        <h1>Expense Tracker</h1>
        <button onClick={logout}>Sign out</button>
      </header>
      <p>You're signed in. Transactions and reports are coming soon.</p>
    </div>
  );
}
