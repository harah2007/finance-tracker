# 💰 Fintrack — Personal Finance Tracker

A local finance tracker built with Python (Flask) + SQLite.
Tracks income & expenses, investments, budgets, goals, and bills.

---

## 🚀 Quick Start

### 1. Make sure Python 3 is installed
```
python3 --version
```

### 2. Install Flask (one-time setup)
```
pip install flask
```
or, if you prefer a virtual environment:
```
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
pip install flask
```

### 3. Run the app
```
python app.py
```

### 4. Open in your browser
```
http://127.0.0.1:5000
```

---

## 📁 File structure
```
finance-tracker/
├── app.py              ← Flask backend + REST API
├── requirements.txt    ← Python dependencies
├── README.md
├── finance.db          ← SQLite database (created on first run)
└── templates/
    └── index.html      ← Full frontend (single page app)
```

## 💾 Data
All your data lives in `finance.db` in the same folder.
Back it up by simply copying that file.

---

## ✨ Features
- **Dashboard** — Monthly income/expense summary, 6-month trend chart, spending by category, recent transactions
- **Transactions** — Add income & expenses, filter by month/year, delete entries
- **Investments** — Track stocks, mutual funds, FDs, crypto, gold, etc. with P&L
- **Budgets** — Set monthly category limits with visual progress bars
- **Goals** — Track savings goals with progress tracking and deadline
- **Bills** — Track recurring bills and subscriptions, mark as paid
