import os
from database import create_cabinet, add_cow, get_animal_status, get_safe_date

def test_system():
    # 1. Reset and Build
    if os.path.exists("livestock.db"): os.remove("livestock.db")
    assert create_cabinet() == True

    # 2. Registration test
    assert add_cow("COW_TEST", "STOLEN", "pic.jpg") == True

    # 3. Status test
    res = get_animal_status("COW_TEST")
    assert res["status"] == "STOLEN"

    # 4. Flexible Timer test (Manual entry)
    # 10 days from March 1st should be March 11th
    safe = get_safe_date("custom_drug", "2026-03-01", manual_days="10")
    assert safe == "2026-03-11"
