const currency = new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" });

export default function TransactionList({ transactions, categories, onDelete }) {
  const categoryNames = Object.fromEntries(categories.map((c) => [c.id, c.name]));

  if (transactions.length === 0) {
    return (
      <div className="card">
        <h2>Transactions</h2>
        <p className="muted">No transactions yet.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Transactions</h2>
      <table className="transaction-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Category</th>
            <th>Description</th>
            <th className="num">Amount</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {transactions.map((t) => (
            <tr key={t.id}>
              <td>{t.transaction_date}</td>
              <td>{categoryNames[t.category_id] || "-"}</td>
              <td>{t.description || ""}</td>
              <td className="num">{currency.format(Number(t.amount))}</td>
              <td className="num">
                <button className="link-button" onClick={() => onDelete(t.id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
