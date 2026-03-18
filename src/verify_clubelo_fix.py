
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from base_elo_engine import DynamicEloEngine
from naming_utils import get_canonical_name

def test_triangulation():
    engine = DynamicEloEngine()
    
    # Test Cases: Iddaa Names -> Expected Canonical -> Expected Source
    test_cases = [
        ("Bayern Münih", "Bayern", "ANCHOR"),
        ("Atalanta", "Atalanta", "ANCHOR"),
        ("Göztepe", "Goeztepe", "ANCHOR"),
        ("Başakşehir", "Bueyueksehir", "ANCHOR"),
        ("FC Bayern München", "Bayern", "ANCHOR"),
        ("Fenerbahçe", "Fenerbahce", "ANCHOR"),
        ("Karagumruk", "Fatih Karaguemruek", "ANCHOR"),
        ("NonExistentTeam", "NonExistentTeam", "DEFAULT_1500")
    ]
    
    print("\n" + "="*60)
    print(" >>> TRIANGULATION ENGINE VERIFICATION TEST <<<")
    print("="*60)
    
    passed_count = 0
    for input_name, expected_canonical, expected_source in test_cases:
        # Get canonical name first (as api_server does)
        # We don't have db_teams here, but get_canonical_name handles empty list
        canonical = get_canonical_name(input_name)
        
        # Get rating from engine
        rating, source = engine.get_rating(canonical)
        
        if source == expected_source:
            passed_count += 1
            print(f"[PASS] Input: {input_name:<20} | Canonical: {canonical:<18} | Rating: {rating:.1f} | Source: {source}")
        else:
            print(f"[FAIL] Input: {input_name:<20} | Canonical: {canonical:<18} | Result Source: {source} (Exp: {expected_source})")
            
    print("-" * 60)
    print(f"SUMMARY: {passed_count}/{len(test_cases)} tests passed.")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_triangulation()
