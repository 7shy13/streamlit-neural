
from naming_utils import get_canonical_name, normalize_turkish

def test_collisions():
    # Mock database names including historical Turkish clubs
    db_names = ["Galatasaray", "Fenerbahce", "Karabukspor", "Besiktas"]
    
    cases = [
        ("Polonya", "Polonya"),          # Should NOT map to Karabukspor
        ("Arnavutluk", "Arnavutluk"),    # Should NOT map to Karabukspor
        ("Kayserispor", "Kayserispor"),  # Should stay Kayserispor (exact or close)
        ("Fenerbahçe", "Fenerbahce"),    # Should map (Turkish char fix)
        ("Liverpool FC", "Liverpool FC") # Should stay original if not in DB
    ]
    
    print("=== NAMING COLLISION TEST ===")
    all_passed = True
    for input_name, expected in cases:
        result = get_canonical_name(input_name, db_names)
        status = "PASS" if result == expected else "FAIL"
        print(f"Input: {input_name:12} | Expected: {expected:12} | Result: {result:12} | {status}")
        if status == "FAIL": all_passed = False
        
    if all_passed:
        print("\n[SUCCESS] No collisions detected with target names.")
    else:
        print("\n[FAILURE] Collisions still detected.")

if __name__ == "__main__":
    test_collisions()
