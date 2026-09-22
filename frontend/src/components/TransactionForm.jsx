import { useState } from "react";
import { api } from "../api/client";

const NEW_CATEGORY = "__new__";

function today() {
  const d = new Date();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${month}-${day}`;
}

export default function TransactionForm({ accounts, categories, onCategoryCreated, onCreated }) {
  const [accountId, setAccountId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [date, setDate] = useState(today);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // fall back to the first account/category until the user picks one
  const selectedAccount = accountId || accounts[0]?.id || "";
  const selectedCategory =
    categoryId || (categories.length ? categories[0].id : NEW_CATEGORY);
  const addingCategory = selectedCategory === NEW_CATEGORY;

  async function resolveCategoryId() {
    if (!addingCategory) return Number(selectedCategory);

    const name = newCategory.trim();
    if (!name) throw new Error("Enter a name for the new category");
    const created = await api.post("/categories", { name });
    onCategoryCreated(created);
    setCategoryId(String(created.id));
    setNewCategory("");
    return created.id;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!selectedAccount) {
      setError("No account found for this user");
      return;
    }
    if (!amount || Number(amount) === 0) {
      setError("Amount must be a non-zero number");
      return;
    }

    setSubmitting(true);
    try {
      const category_id = await resolveCategoryId();
      const created = await api.post("/transactions", {
        account_id: Number(selectedAccount),
        category_id,
        amount,
        description: description.trim() || null,
        transaction_date: date,
      });
      onCreated(created);
      setAmount("");
      setDescription("");
    } catch (err) {
      setError(err.message || "Could not save transaction");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="card transaction-form" onSubmit={handleSubmit}>
      <h2>Add transaction</h2>
      <div className="form-grid">
        {accounts.length > 1 && (
          <label>
            Account
            <select value={selectedAccount} onChange={(e) => setAccountId(e.target.value)}>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          Category
          <select value={selectedCategory} onChange={(e) => setCategoryId(e.target.value)}>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
            <option value={NEW_CATEGORY}>+ New category</option>
          </select>
        </label>
        {addingCategory && (
          <label>
            New category name
            <input
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              maxLength={100}
              required
            />
          </label>
        )}
        <label>
          Amount
          <input
            type="number"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
          />
        </label>
        <label>
          Date
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
        </label>
        <label className="span-2">
          Description
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={255}
            placeholder="Optional"
          />
        </label>
      </div>
      {error && <p className="form-error">{error}</p>}
      <button type="submit" disabled={submitting}>
        {submitting ? "Saving..." : "Add"}
      </button>
    </form>
  );
}
