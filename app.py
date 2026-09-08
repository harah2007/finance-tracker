from flask import Flask, render_template, request, jsonify
import sqlite3
import calendar
from datetime import date

app = Flask(__name__)
DB_PATH = 'finance.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        type TEXT NOT NULL,
        notes TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS investments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        amount_invested REAL NOT NULL,
        current_value REAL NOT NULL,
        date_added TEXT NOT NULL,
        notes TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL UNIQUE,
        monthly_limit REAL NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        target_amount REAL NOT NULL,
        current_amount REAL NOT NULL DEFAULT 0,
        deadline TEXT,
        notes TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        due_day INTEGER NOT NULL,
        frequency TEXT NOT NULL,
        category TEXT NOT NULL,
        is_paid INTEGER DEFAULT 0,
        last_paid TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        balance REAL NOT NULL DEFAULT 0,
        bank TEXT,
        notes TEXT,
        last_updated TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()

# ── Transactions ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    conn = get_db()
    month = request.args.get('month')
    year  = request.args.get('year')
    q, p = 'SELECT * FROM transactions', []
    if month and year:
        q += ' WHERE strftime("%m", date)=? AND strftime("%Y", date)=?'
        p = [month.zfill(2), year]
    q += ' ORDER BY date DESC'
    rows = conn.execute(q, p).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    d = request.json
    conn = get_db()
    conn.execute(
        'INSERT INTO transactions (date,description,amount,category,type,notes) VALUES (?,?,?,?,?,?)',
        (d['date'], d['description'], d['amount'], d['category'], d['type'], d.get('notes',''))
    )
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/transactions/<int:tid>', methods=['PUT'])
def update_transaction(tid):
    d = request.json
    conn = get_db()
    conn.execute(
        'UPDATE transactions SET date=?,description=?,amount=?,category=?,type=?,notes=? WHERE id=?',
        (d['date'], d['description'], d['amount'], d['category'], d['type'], d.get('notes',''), tid)
    )
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/transactions/import', methods=['POST'])
def import_transactions():
    rows = request.json  # list of transaction dicts
    if not rows:
        return jsonify({'success': False, 'message': 'No data'}), 400
    conn = get_db()
    count = 0
    for r in rows:
        try:
            conn.execute(
                'INSERT INTO transactions (date,description,amount,category,type,notes) VALUES (?,?,?,?,?,?)',
                (r['date'], r['description'], float(r['amount']), r.get('category','Other'), r['type'], r.get('notes',''))
            )
            count += 1
        except Exception:
            continue
    conn.commit(); conn.close()
    return jsonify({'success': True, 'imported': count})

@app.route('/api/transactions/<int:tid>', methods=['DELETE'])
def delete_transaction(tid):
    conn = get_db()
    conn.execute('DELETE FROM transactions WHERE id=?', (tid,))
    conn.commit(); conn.close()
    return jsonify({'success': True})

# ── Summary ───────────────────────────────────────────────────────────────────

@app.route('/api/summary')
def get_summary():
    conn = get_db()
    today = date.today()
    m, y = str(today.month).zfill(2), str(today.year)

    def scalar(sql, params=()):
        return conn.execute(sql, params).fetchone()[0] or 0

    income  = scalar('SELECT SUM(amount) FROM transactions WHERE type="income"  AND strftime("%m",date)=? AND strftime("%Y",date)=?', (m,y))
    expense = scalar('SELECT SUM(amount) FROM transactions WHERE type="expense" AND strftime("%m",date)=? AND strftime("%Y",date)=?', (m,y))
    port_val = scalar('SELECT SUM(current_value)   FROM investments')
    port_inv = scalar('SELECT SUM(amount_invested) FROM investments')

    cat_rows = conn.execute(
        'SELECT category, SUM(amount) as total FROM transactions WHERE type="expense" AND strftime("%m",date)=? AND strftime("%Y",date)=? GROUP BY category ORDER BY total DESC',
        (m,y)
    ).fetchall()

    trend = []
    for i in range(5, -1, -1):
        mi = today.month - i
        yi = today.year
        while mi <= 0: mi += 12; yi -= 1
        ms, ys = str(mi).zfill(2), str(yi)
        inc = scalar('SELECT SUM(amount) FROM transactions WHERE type="income"  AND strftime("%m",date)=? AND strftime("%Y",date)=?', (ms,ys))
        exp = scalar('SELECT SUM(amount) FROM transactions WHERE type="expense" AND strftime("%m",date)=? AND strftime("%Y",date)=?', (ms,ys))
        trend.append({'month': calendar.month_abbr[mi], 'income': inc, 'expense': exp})

    liquid   = scalar('SELECT SUM(balance) FROM accounts')
    net_worth = port_val + liquid

    conn.close()
    return jsonify({
        'monthly_income': income, 'monthly_expense': expense,
        'net': income - expense,
        'portfolio_value': port_val, 'portfolio_invested': port_inv,
        'cat_spending': [dict(r) for r in cat_rows],
        'monthly_trend': trend,
        'liquid': liquid,
        'net_worth': net_worth
    })

# ── Accounts ──────────────────────────────────────────────────────────────────

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    conn = get_db()
    rows = conn.execute('SELECT * FROM accounts ORDER BY type, name').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/accounts', methods=['POST'])
def add_account():
    d = request.json
    conn = get_db()
    conn.execute(
        'INSERT INTO accounts (name,type,balance,bank,notes,last_updated) VALUES (?,?,?,?,?,?)',
        (d['name'], d['type'], d['balance'], d.get('bank',''), d.get('notes',''), date.today().isoformat())
    )
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/accounts/<int:aid>', methods=['PUT'])
def update_account(aid):
    d = request.json
    conn = get_db()
    conn.execute(
        'UPDATE accounts SET name=?,type=?,balance=?,bank=?,notes=?,last_updated=? WHERE id=?',
        (d['name'], d['type'], d['balance'], d.get('bank',''), d.get('notes',''), date.today().isoformat(), aid)
    )
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/accounts/<int:aid>', methods=['DELETE'])
def delete_account(aid):
    conn = get_db()
    conn.execute('DELETE FROM accounts WHERE id=?', (aid,))
    conn.commit(); conn.close()
    return jsonify({'success': True})

# ── Investments ───────────────────────────────────────────────────────────────

@app.route('/api/investments', methods=['GET'])
def get_investments():
    conn = get_db()
    rows = conn.execute('SELECT * FROM investments ORDER BY current_value DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/investments', methods=['POST'])
def add_investment():
    d = request.json
    conn = get_db()
    conn.execute(
        'INSERT INTO investments (name,type,amount_invested,current_value,date_added,notes) VALUES (?,?,?,?,?,?)',
        (d['name'], d['type'], d['amount_invested'], d['current_value'], d['date_added'], d.get('notes',''))
    )
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/investments/<int:iid>', methods=['PUT'])
def update_investment(iid):
    d = request.json
    conn = get_db()
    conn.execute(
        'UPDATE investments SET name=?,type=?,amount_invested=?,current_value=?,notes=? WHERE id=?',
        (d['name'], d['type'], d['amount_invested'], d['current_value'], d.get('notes',''), iid)
    )
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/investments/<int:iid>', methods=['DELETE'])
def delete_investment(iid):
    conn = get_db()
    conn.execute('DELETE FROM investments WHERE id=?', (iid,))
    conn.commit(); conn.close()
    return jsonify({'success': True})

# ── Budgets ───────────────────────────────────────────────────────────────────

@app.route('/api/budgets', methods=['GET'])
def get_budgets():
    conn = get_db()
    today = date.today()
    m, y = str(today.month).zfill(2), str(today.year)
    budgets = conn.execute('SELECT * FROM budgets').fetchall()
    result = []
    for b in budgets:
        spent = conn.execute(
            'SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type="expense" AND category=? AND strftime("%m",date)=? AND strftime("%Y",date)=?',
            (b['category'], m, y)
        ).fetchone()[0]
        result.append({**dict(b), 'spent': spent})
    conn.close()
    return jsonify(result)

@app.route('/api/budgets', methods=['POST'])
def add_budget():
    d = request.json
    conn = get_db()
    conn.execute('INSERT OR REPLACE INTO budgets (category,monthly_limit) VALUES (?,?)', (d['category'], d['monthly_limit']))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/budgets/<int:bid>', methods=['DELETE'])
def delete_budget(bid):
    conn = get_db()
    conn.execute('DELETE FROM budgets WHERE id=?', (bid,))
    conn.commit(); conn.close()
    return jsonify({'success': True})

# ── Goals ─────────────────────────────────────────────────────────────────────

@app.route('/api/goals', methods=['GET'])
def get_goals():
    conn = get_db()
    rows = conn.execute('SELECT * FROM goals ORDER BY deadline').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/goals', methods=['POST'])
def add_goal():
    d = request.json
    conn = get_db()
    conn.execute(
        'INSERT INTO goals (name,target_amount,current_amount,deadline,notes) VALUES (?,?,?,?,?)',
        (d['name'], d['target_amount'], d.get('current_amount', 0), d.get('deadline',''), d.get('notes',''))
    )
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/goals/<int:gid>', methods=['PUT'])
def update_goal(gid):
    d = request.json
    conn = get_db()
    conn.execute(
        'UPDATE goals SET name=?,target_amount=?,current_amount=?,deadline=?,notes=? WHERE id=?',
        (d['name'], d['target_amount'], d['current_amount'], d.get('deadline',''), d.get('notes',''), gid)
    )
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/goals/<int:gid>', methods=['DELETE'])
def delete_goal(gid):
    conn = get_db()
    conn.execute('DELETE FROM goals WHERE id=?', (gid,))
    conn.commit(); conn.close()
    return jsonify({'success': True})

# ── Bills ─────────────────────────────────────────────────────────────────────

@app.route('/api/bills', methods=['GET'])
def get_bills():
    conn = get_db()
    rows = conn.execute('SELECT * FROM bills ORDER BY due_day').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/bills', methods=['POST'])
def add_bill():
    d = request.json
    conn = get_db()
    conn.execute(
        'INSERT INTO bills (name,amount,due_day,frequency,category,is_paid) VALUES (?,?,?,?,?,0)',
        (d['name'], d['amount'], d['due_day'], d['frequency'], d['category'])
    )
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/bills/<int:bid>/toggle', methods=['POST'])
def toggle_bill(bid):
    conn = get_db()
    paid = conn.execute('SELECT is_paid FROM bills WHERE id=?', (bid,)).fetchone()['is_paid']
    new_status = 0 if paid else 1
    last_paid  = date.today().isoformat() if new_status else None
    conn.execute('UPDATE bills SET is_paid=?,last_paid=? WHERE id=?', (new_status, last_paid, bid))
    conn.commit(); conn.close()
    return jsonify({'success': True, 'is_paid': new_status})

@app.route('/api/bills/<int:bid>', methods=['DELETE'])
def delete_bill(bid):
    conn = get_db()
    conn.execute('DELETE FROM bills WHERE id=?', (bid,))
    conn.commit(); conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    print("\n✅  Finance Tracker is running!")
    print("🌐  Open http://127.0.0.1:5000 in your browser\n")
    app.run(debug=True)
