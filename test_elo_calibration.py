from base_elo_engine import DynamicEloEngine

def test_calibration():
    engine = DynamicEloEngine()
    
    # We'll test with names that should trigger the Anchor logic
    test_cases = [
        ("Liverpool FC", "Liverpool"), 
        ("Galatasaray", "Galatasaray"),
        ("Manchester City", "Man City"),
        ("Fenerbahce", "Fenerbahce"),
        ("Real Madrid", "Real Madrid")
    ]
    
    print("--- Ground Truth Elo Integration Check ---")
    for sr_name, display_name in test_cases:
        rating = engine.get_rating(sr_name)
        print(f"{sr_name:20} -> Elo: {rating:.2f}")

if __name__ == "__main__":
    test_calibration()

if __name__ == "__main__":
    test_calibration()
