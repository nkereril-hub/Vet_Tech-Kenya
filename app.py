from flask import Flask, render_template, request, redirect, url_for, session, flash
import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = "vettech_secret_key_2026"

DB_FILE = "vettech_data.db"

# Updated DRUG_DATA with separate milk and meat periods
DRUG_DATA = {
    'tetracycline': {'meat': 28, 'milk': 7},
    'penicillin': {'meat': 14, 'milk': 3}, 
    'ivermectin': {'meat': 35, 'milk': 0}, 
    'albendazole': {'meat': 14, 'milk': 3},
    'penistrep': {'meat': 23, 'milk': 3}  
}

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users 
                        (username TEXT PRIMARY KEY, password TEXT, role TEXT, kvb_number TEXT, name TEXT)''')
        
        # TABLE UPDATED: milk_safe_date and meat_safe_date are now separate
        conn.execute('''CREATE TABLE IF NOT EXISTS records 
                        (animal_id TEXT PRIMARY KEY, species TEXT, drug TEXT, 
                         treatment_date TEXT, milk_safe_date TEXT, meat_safe_date TEXT, 
                         farmer_phone TEXT, vet_kvb TEXT)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS system_flags 
                        (flag_name TEXT PRIMARY KEY, status TEXT)''')
        conn.execute("INSERT OR IGNORE INTO system_flags VALUES ('rover_command', 'IDLE')")
        conn.commit()

init_db()

# ====================== ROUTES ======================

@app.route("/")
def index():
    if 'username' not in session:
        return redirect(url_for("login"))
    
    with get_db_connection() as conn:
        records = conn.execute("""
            SELECT * FROM records 
            ORDER BY treatment_date DESC LIMIT 50
        """).fetchall()
    
    return render_template("index.html", 
                         username=session.get('display_name'),
                         role=session.get('role'),
                         vet_kvb=session.get('vet_kvb'),
                         drugs=DRUG_DATA,
                         records=records,
                         datetime=datetime,
                         today=datetime.date.today())


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        role = request.form.get("role")
        username = request.form.get("username", "").strip()
        pwd = request.form.get("password", "").strip()
        name = request.form.get("name", "").strip()
        kvb = request.form.get("kvb", "").strip() if role == "vet" else "N/A"
        
        if not username or not pwd:
            flash("❌ Username and Password are required.", "danger")
            return redirect(url_for("signup"))

        try:
            with get_db_connection() as conn:
                conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", 
                           (username, pwd, role, kvb, name))
                conn.commit()
            flash("✅ Account created successfully! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("❌ Username already taken.", "warning")
            
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        pwd = request.form.get("password", "").strip()
        
        with get_db_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", 
                              (username, pwd)).fetchone()
        
        if user:
            session.update({
                'username': user['username'],
                'role': user['role'],
                'vet_kvb': user['kvb_number'],
                'display_name': user['name'] or user['username']
            })
            flash(f"✅ Welcome back, {session['display_name']}!", "success")
            return redirect(url_for("index"))
        
        flash("❌ Invalid credentials.", "danger")
    return render_template("login.html")


@app.route("/treatment", methods=["POST"])
def treatment():
    if session.get('role') != 'vet':
        flash("❌ Only veterinarians can log treatments.", "danger")
        return redirect(url_for("index"))

    animal_id = request.form.get("animal_id", "").strip()
    drug_input = request.form.get("drug", "").strip().lower()
    
    if not animal_id or drug_input not in DRUG_DATA:
        flash("❌ Invalid animal or drug.", "warning")
        return redirect(url_for("index"))

    today = datetime.date.today()
    meat_days = DRUG_DATA[drug_input]['meat']
    milk_days = DRUG_DATA[drug_input]['milk']
    
    meat_safe_date = today + datetime.timedelta(days=meat_days)
    milk_safe_date = today + datetime.timedelta(days=milk_days)
    
    with get_db_connection() as conn:
        # REPLACE INTO now handles 8 columns total
        conn.execute("REPLACE INTO records VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                     (animal_id, "Cattle", drug_input, str(today), 
                      str(milk_safe_date), str(meat_safe_date), "0700000", session['vet_kvb']))
        conn.commit()
    
    flash(f"✅ {animal_id} treated. Milk Safe: {milk_safe_date} | Meat Safe: {meat_safe_date}", "success")
    return redirect(url_for("index"))


@app.route("/bulk_treatment", methods=["POST"])
def bulk_treatment():
    if session.get('role') != 'vet':
        flash("❌ Unauthorized.", "danger")
        return redirect(url_for("index"))

    drug_input = request.form.get("drug", "").strip().lower()
    scanned_count = int(request.form.get("scanned_count", 0))

    if drug_input not in DRUG_DATA or scanned_count <= 0:
        flash("❌ Invalid request.", "warning")
        return redirect(url_for("index"))

    today = datetime.date.today()
    meat_safe_date = str(today + datetime.timedelta(days=DRUG_DATA[drug_input]['meat']))
    milk_safe_date = str(today + datetime.timedelta(days=DRUG_DATA[drug_input]['milk']))
    today_str = str(today)

    with get_db_connection() as conn:
        for i in range(1, scanned_count + 1):
            animal_id = f"SCANNED-{i:03d}"
            conn.execute("REPLACE INTO records VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                         (animal_id, "Cattle", drug_input, today_str, 
                          milk_safe_date, meat_safe_date, "0700000", session['vet_kvb']))
        conn.commit()

    flash(f"✅ Bulk treatment applied. Milk: {milk_safe_date}, Meat: {meat_safe_date}", "success")
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    # Ensure tables exist before running
    init_db()
    app.run(debug=True)
