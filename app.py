import sqlite3
import scanner  # This links to your biometric scanner.py
import numpy as np
import io
from datetime import datetime, timedelta

# --- 1. DATABASE ADAPTERS (Essential for Biometric math) ---
def adapt_array(arr):
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())

def convert_array(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)

sqlite3.register_adapter(np.ndarray, adapt_array)
sqlite3.register_converter("ARRAY", convert_array)

# --- 2. DATABASE ARCHITECTURE ---
def init_db():
    # detect_types allows the app to read back the AI encodings
    conn = sqlite3.connect('vet_tech_pro.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # Updated livestock table with Biometric (ARRAY) support
    cursor.execute('''CREATE TABLE IF NOT EXISTS livestock (
        muzzle_id TEXT PRIMARY KEY,
        biometric_encoding ARRAY,    -- NEW: The 128-digit AI fingerprint
        owner_phone TEXT,
        last_drug TEXT,
        milk_safe_date TEXT,
        meat_safe_date TEXT,
        is_zoonotic_alert INTEGER DEFAULT 0,
        is_synced INTEGER DEFAULT 0
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS drug_registry (
        drug_name TEXT PRIMARY KEY, milk_days INTEGER, meat_days INTEGER
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS wallets (phone TEXT PRIMARY KEY, points INTEGER DEFAULT 0)''')
    
    cursor.executemany("INSERT OR IGNORE INTO drug_registry VALUES (?,?,?)",
                       [('Penistrep', 3, 28), ('Oxytet', 5, 21), ('Dewormer', 0, 14)])

    conn.commit()
    conn.close()

# --- 3. DYNAMIC LOGIC FUNCTIONS ---

def get_withdrawal_dates(drug_name):
    conn = sqlite3.connect('vet_tech_pro.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute("SELECT milk_days, meat_days FROM drug_registry WHERE drug_name COLLATE NOCASE = ?", (drug_name,))
    result = cursor.fetchone()
    conn.close()

    if result:
        milk, meat = result
    else:
        print(f"\n⚠️ Drug '{drug_name}' not found.")
        milk = int(input(f"Enter Milk withdrawal days: "))
        meat = int(input(f"Enter Meat withdrawal days: "))
        # Save new drug to registry
        conn = sqlite3.connect('vet_tech_pro.db'); cursor = conn.cursor()
        cursor.execute("INSERT INTO drug_registry VALUES (?,?,?)", (drug_name, milk, meat))
        conn.commit(); conn.close()

    today = datetime.now()
    return (today + timedelta(days=milk)).strftime("%Y-%m-%d"), (today + timedelta(days=meat)).strftime("%Y-%m-%d")

# --- 4. THE USSD INTERFACE (*384# SIMULATION) ---

def main_menu():
    print("\n" + "="*45)
    print("      VET-TECH: ONE HEALTH ECOSYSTEM")
    print("="*45)
    print("1. Register Animal (Biometric Scan)")
    print("2. Treatment & Safety Check (Scan muzzle)")
    print("3. Bonga-Afya (E-Waste & Points)")
    print("4. EMERGENCY (Zoonotic Alert)")
    print("5. Sync Field Data (Offline -> Cloud)")
    print("0. Exit")

    choice = input("\nSelect Option: ")
    conn = sqlite3.connect('vet_tech_pro.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    if choice == '1':
        print("\n--- 📸 STARTING BIOMETRIC REGISTRATION ---")
        img_path = input("Enter path to muzzle photo (e.g., muzzle_scans/cow1.jpg): ")
        scan_result = scanner.process_and_encode(img_path)
        
        if isinstance(scan_result, np.ndarray):
            m_id = input("Assign Animal ID (e.g., ISIOLO-001): ").strip().upper()
            phone = input("Owner Phone: ")
            cursor.execute("INSERT OR REPLACE INTO livestock (muzzle_id, biometric_encoding, owner_phone, is_synced) VALUES (?,?,?,0)",
                           (m_id, scan_result, phone))
            print(f"✅ SUCCESS: {m_id} registered with unique Biometric ID.")
        else:
            print(f"❌ SCAN FAILED: {scan_result}")

    elif choice == '2':
        print("\n--- 🔍 SCANNING FOR IDENTIFICATION ---")
        img_path = input("Enter path to scan muzzle: ")
        scan_result = scanner.process_and_encode(img_path)
        
        if isinstance(scan_result, np.ndarray):
            # Match current scan against the whole database
            cursor.execute("SELECT muzzle_id, biometric_encoding, last_drug, meat_safe_date FROM livestock")
            found = False
            for row in cursor.fetchall():
                import face_recognition # Temporary import for comparison
                match = face_recognition.compare_faces([row[1]], scan_result, tolerance=0.5)
                if match[0]:
                    print(f"✅ MATCH FOUND: Animal {row[0]}")
                    print(f"Last Treatment: {row[2]} | Meat Safe: {row[3]}")
                    
                    # Log new treatment
                    drug = input("New Drug Administered (or skip): ").strip()
                    if drug:
                        milk, meat = get_withdrawal_dates(drug)
                        cursor.execute("UPDATE livestock SET last_drug=?, milk_safe_date=?, meat_safe_date=?, is_synced=0 WHERE muzzle_id=?",
                                       (drug, milk, meat, row[0]))
                        print(f"✅ RECORDED: Safety dates updated.")
                    found = True
                    break
            if not found: print("❓ Unknown animal. Please register first.")
        else:
            print(f"❌ SCAN FAILED: {scan_result}")

    elif choice == '3':
        phone = input("Farmer Phone: "); kg = float(input("E-Waste Weight (Kg): "))
        cursor.execute("INSERT OR IGNORE INTO wallets VALUES (?, 0)")
        cursor.execute("UPDATE wallets SET points = points + ? WHERE phone = ?", (kg*10, phone))
        print(f"✅ Points Awarded.")

    elif choice == '5':
        cursor.execute("UPDATE livestock SET is_synced = 1")
        print("🔄 SYNC COMPLETE.")

    conn.commit(); conn.close()

if __name__ == "__main__":
    init_db()
    while True: main_menu()