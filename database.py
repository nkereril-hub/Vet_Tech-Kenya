import sqlite3
import numpy as np
import io
from datetime import datetime, timedelta

# --- YOUR EXISTING MEDICINE RULES ---
MEDICINE_RULES = {
    "penicillin": 7,
    "tetracycline": 28,
    "dewormer": 3
}

DB_NAME = "livestock.db"

# --- NEW: BIOMETRIC ADAPTERS (For Offline AI Data) ---
def adapt_array(arr):
    """Converts a numpy array (biometric ID) to binary for SQLite."""
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())

def convert_array(text):
    """Converts binary data back into a numpy array."""
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)

# Register the adapters with sqlite3
sqlite3.register_adapter(np.ndarray, adapt_array)
sqlite3.register_converter("ARRAY", convert_array)

def create_cabinet():
    """Creates the database with Biometric and AMR support."""
    # detect_types allows us to read back the biometric array automatically
    connection = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    
    # Updated table to include biometric_id (ARRAY) and drug_info
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cows (
            id TEXT PRIMARY KEY,
            status TEXT,
            muzzle_image TEXT,
            biometric_id ARRAY,        -- NEW: Stores the 128-digit AI ID
            kvb_number TEXT,          -- NEW: Prevents quacks
            withdrawal_date TEXT       -- NEW: Tracks AMR safety
        )
    """)
    connection.commit()
    connection.close()
    return True

# --- ENHANCED: REGISTER NEW ANIMAL ---
def add_cow(cow_id, status="Healthy", image_path="none.jpg", biometric_data=None, kvb="PENDING"):
    """Registers a new cow with its biometric ID and Vet KVB number."""
    connection = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO cows (id, status, muzzle_image, biometric_id, kvb_number) 
            VALUES (?, ?, ?, ?, ?)
        """, (cow_id, status, image_path, biometric_data, kvb))
        connection.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    finally:
        connection.close()
    return success

# --- ENHANCED: STATUS & BIOMETRIC CHECK ---
def get_animal_details(cow_id):
    """Retrieves full details including the biometric ID for matching."""
    connection = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    cursor.execute("SELECT status, muzzle_image, biometric_id, withdrawal_date FROM cows WHERE id = ?", (cow_id,))
    result = cursor.fetchone()
    connection.close()
    
    if result:
        return {
            "status": result[0], 
            "image": result[1], 
            "biometric": result[2],
            "safe_date": result[3]
        }
    return None

# --- YOUR EXISTING WITHDRAWAL LOGIC ---
def get_safe_date(drug_name, treatment_date_str, manual_days=None):
    """Calculates withdrawal date. Prioritizes vet's manual input."""
    if manual_days:
        try:
            days_to_wait = int(manual_days)
        except ValueError:
            return "ERROR: Invalid days"
    else:
        days_to_wait = MEDICINE_RULES.get(drug_name.lower(), 0)

    try:
        date_given = datetime.strptime(treatment_date_str.strip(), "%Y-%m-%d")
        safe_date = date_given + timedelta(days=days_to_wait)
        return safe_date.strftime("%Y-%m-%d")
    except ValueError:
        return "ERROR: Use YYYY-MM-DD"

# --- NEW: UPDATE WITHDRAWAL STATUS ---
def update_treatment(cow_id, drug_name, date_given):
    """Updates the AMR safety date in the database."""
    safe_date = get_safe_date(drug_name, date_given)
    if "ERROR" in safe_date:
        return safe_date
    
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    cursor.execute("UPDATE cows SET withdrawal_date = ? WHERE id = ?", (safe_date, cow_id))
    connection.commit()
    connection.close()
    return f"Success: Animal safe after {safe_date}"

if __name__ == "__main__":
    create_cabinet()
    print("VET-KENYA Engine (Biometric + AMR Ready) Loaded.")