from flask import Flask, render_template, request, redirect, url_for, session, flash
import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = "vettech_secret_key_2026"

DB_FILE = "vettech_data.db"

# Updated DRUG_DATA with separate milk and meat periods
DRUG_DATA = {
    'tetracycline': {'meat': 28, 'milk': 7},
    'penicillin': {'meat': 14, 'milk': 3}, # 72 hours approx 3 days
    'ivermectin': {'meat': 35, 'milk': 0}, # Note: Often not used in milking cows
    'albendazole': {'meat': 14, 'milk': 3},
    'penistrep': {'meat': 23, 'milk': 3}  # 60-72 hours
}

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users 
                        (username TEXT PRIMARY KEY, password TEXT, role TEXT, kvb_number TEXT, name TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS records 
                        (animal_id TEXT PRIMARY KEY, species TEXT, drug TEXT, 
                         treatment_date TEXT, safe_date TEXT, farmer_phone TEXT, vet_kvb TEXT)''')
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
    
    # Get recent scanned/treatment records for display
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
                         datetime=datetime,  # CRITICAL: Added so HTML can do logic
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

    # FIX: Extracting 'meat' days specifically for the database math
    safe_days = DRUG_DATA[drug_input]['meat']
    safe_date = datetime.date.today() + datetime.timedelta(days=safe_days)
    
    with get_db_connection() as conn:
        conn.execute("REPLACE INTO records VALUES (?, ?, ?, ?, ?, ?, ?)", 
                     (animal_id, "Cattle", drug_input, str(datetime.date.today()), 
                      str(safe_date), "0700000", session['vet_kvb']))
        conn.commit()
    
    flash(f"✅ {animal_id} treated with {drug_input}. Safe on {safe_date}.", "success")
    return redirect(url_for("index"))


# New: Bulk treatment for all scanned animals
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

    # FIX: Using 'meat' as the standard safe period for bulk entries
    safe_days = DRUG_DATA[drug_input]['meat']
    safe_date = datetime.date.today() + datetime.timedelta(days=safe_days)
    today = str(datetime.date.today())

    # For demo: We simulate treating "SCANNED-001" to "SCANNED-XXX"
    with get_db_connection() as conn:
        for i in range(1, scanned_count + 1):
            animal_id = f"SCANNED-{i:03d}"
            conn.execute("REPLACE INTO records VALUES (?, ?, ?, ?, ?, ?, ?)", 
                         (animal_id, "Cattle", drug_input, today, 
                          str(safe_date), "0700000", session['vet_kvb']))
        conn.commit()

    flash(f"✅ Bulk treatment applied to {scanned_count} animals with {drug_input}. Safe on {safe_date}.", "success")
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
