
import difflib

# Mapping of Scraped Names (Iddaa) to Historical Names (CSV/Elo Engine)
# Key: Scraped Name, Value: Database Name
# MASTER ALIAS REGISTRY: Centralized bridge for all naming spaces.
# Any variant (Iddaa, CSV, ClubElo, TM) maps to a single Canonical Key.
MASTER_ALIAS_REGISTRY = {
    # --- TURKEY: Süper Lig ---
    "Fenerbahçe": "Fenerbahce", "Fenerbahce SK": "Fenerbahce",
    "Galatasaray": "Galatasaray", "Galatasaray SK": "Galatasaray",
    "Beşiktaş": "Besiktas", "Besiktas JK": "Besiktas",
    "Trabzonspor": "Trabzonspor",
    "Başakşehir": "Bueyueksehir", "Bașakșehir": "Bueyueksehir", "Bašakšehir": "Bueyueksehir", "Buyuksehyr": "Bueyueksehir", "Istanbul Basaksehir": "Bueyueksehir",
    "Kasımpaşa": "Kasimpasa", "Kasimpasa SK": "Kasimpasa",
    "Göztepe": "Goeztepe", "Goztep": "Goeztepe", "Goztepe SK": "Goeztepe",
    "Antalyaspor": "Antalyaspor",
    "Konyaspor": "Konyaspor",
    "Kayserispor": "Kayseri", "Kayseri": "Kayseri",
    "Sivasspor": "Sivasspor",
    "Alanyaspor": "Alanyaspor",
    "Adana Demirspor": "Adana Demirspor", "Ad. Demirspor": "Adana Demirspor",
    "Ankaragücü": "Ankaraguecue", "MKE Ankaragücü": "Ankaraguecue",
    "Fatih Karagümrük": "Fatih Karaguemruek", "Karagumruk": "Fatih Karaguemruek",
    "İstanbulspor": "Istanbulspor",
    "Rizespor": "Rizespor", "Caykur Rizespor": "Rizespor",
    "Samsunspor": "Samsunspor",
    "Gaziantep FK": "Gaziantep FK", "Gaziantep": "Gaziantep FK",
    "Hatayspor": "Hatayspor",
    "Eyüpspor": "Eyupspor",
    "Bodrum FK": "Bodrum",
    
    # --- GERMANY: Bundesliga ---
    "Bayern Münih": "Bayern", "Bayern Munich": "Bayern", "FC Bayern München": "Bayern", "Bayern Muenchen": "Bayern",
    "B. Leverkusen": "Leverkusen", "Bayer Leverkusen": "Leverkusen", "Bayer 04 Leverkusen": "Leverkusen",
    "Dortmund": "Dortmund", "Borussia Dortmund": "Dortmund", "BVB": "Dortmund",
    "Leipzig": "RB Leipzig", "RB Leipzig": "RB Leipzig",
    "Stuttgart": "Stuttgart", "VfB Stuttgart": "Stuttgart",
    "Frankfurt": "Frankfurt", "Eintracht Frankfurt": "Frankfurt",
    "Hoffenheim": "Hoffenheim", "TSG Hoffenheim": "Hoffenheim",
    "Mainz": "Mainz", "FSV Mainz 05": "Mainz", "Mainz 05": "Mainz",
    "Freiburg": "Freiburg", "SC Freiburg": "Freiburg",
    "Werder": "Werder", "Werder Bremen": "Werder",
    "Wolfsburg": "Wolfsburg", "VfL Wolfsburg": "Wolfsburg",
    "Augsburg": "Augsburg", "FC Augsburg": "Augsburg",
    "Gladbach": "Gladbach", "Moenchengladbach": "Gladbach", "Borussia M'gladbach": "Gladbach",
    
    # --- ITALY: Serie A ---
    "Inter": "Inter", "Internazionale": "Inter", "Inter Milan": "Inter",
    "Milan": "Milan", "AC Milan": "Milan",
    "Juventus": "Juventus", "Juve": "Juventus",
    "Napoli": "Napoli", "SSC Napoli": "Napoli",
    "Atalanta": "Atalanta", "Atalanta BC": "Atalanta",
    "Roma": "Roma", "AS Roma": "Roma",
    "Lazio": "Lazio", "SS Lazio": "Lazio",
    "Fiorentina": "Fiorentina", "ACF Fiorentina": "Fiorentina",
    "Bologna": "Bologna", "Bologna FC": "Bologna",
    "Torino": "Torino", "Torino FC": "Torino",
    "Monza": "Monza", "AC Monza": "Monza",
    
    # --- SPAIN: La Liga ---
    "Real Madrid": "Real Madrid",
    "Barcelona": "Barcelona", "FC Barcelona": "Barcelona", "Barca": "Barcelona",
    "Atletico": "Atletico", "Atalanta": "Atalanta", "Atletico Madrid": "Atletico", "Atalanta BC": "Atalanta", # Fix collision
    "Sociedad": "Sociedad", "Real Sociedad": "Sociedad",
    "Bilbao": "Bilbao", "Athletic Bilbao": "Bilbao", "Athletic Club": "Bilbao",
    "Girona": "Girona", "Girona FC": "Girona",
    "Betis": "Betis", "Real Betis": "Betis",
    "Sevilla": "Sevilla", "Sevilla FC": "Sevilla",
    "Valencia": "Valencia", "Valencia CF": "Valencia",
    "Villarreal": "Villarreal", "Villarreal CF": "Villarreal",
    
    # --- ENGLAND: Premier League ---
    "Man City": "Man City", "Manchester City": "Man City",
    "Liverpool": "Liverpool", "Liverpool FC": "Liverpool",
    "Arsenal": "Arsenal", "Arsenal FC": "Arsenal",
    "Aston Villa": "Aston Villa",
    "Tottenham": "Tottenham", "Tottenham Hotspur": "Tottenham", "Spurs": "Tottenham",
    "Chelsea": "Chelsea", "Chelsea FC": "Chelsea",
    "Newcastle": "Newcastle", "Newcastle United": "Newcastle",
    "Man United": "Man United", "Manchester United": "Man United", "Man Utd": "Man United",
    "West Ham": "West Ham", "West Ham United": "West Ham",
    "Brighton": "Brighton", "Brighton & Hove Albion": "Brighton",
    
    # --- FRANCE: Ligue 1 ---
    "PSG": "Paris SG", "Paris SG": "Paris SG", "Paris Saint-Germain": "Paris SG",
    "Monaco": "Monaco", "AS Monaco": "Monaco",
    "Lille": "Lille", "LOSC Lille": "Lille",
    "Brest": "Brest", "Stade Brestois 29": "Brest",
    "Nice": "Nice", "OGC Nice": "Nice",
    "Lyon": "Lyon", "Olympique Lyonnais": "Lyon",
    "Marseille": "Marseille", "Olympique de Marseille": "Marseille",
    "Lens": "Lens", "RC Lens": "Lens",
    "Rennes": "Rennes", "Stade Rennais": "Rennes",
}

# Reverse map for database names lookup
REVERSE_ALIAS_REGISTRY = {v: k for k, v in MASTER_ALIAS_REGISTRY.items()}

def normalize_turkish(text, clubelo_style=False):
    """
    Replaces Turkish characters with ASCII equivalents.
    If clubelo_style=True, uses German-style transcription (ü -> ue, ö -> oe).
    """
    if not text: return ""
    
    if clubelo_style:
        # Transcription rules for ClubElo (Germanic style)
        trans = {
            'ü': 'ue', 'ö': 'oe', 'Ü': 'Ue', 'Ö': 'Oe',
            'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ş': 's',
            'Ç': 'C', 'Ğ': 'G', 'İ': 'I', 'Ş': 'S'
        }
        for k, v in trans.items():
            text = text.replace(k, v)
    else:
        # Standard simplification
        chars = {
            'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
            'Ç': 'C', 'Ğ': 'G', 'İ': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U'
        }
        for k, v in chars.items():
            text = text.replace(k, v)
    return text

# National teams to prevent club-level fuzzy collisions
NATIONAL_TEAMS = [
    "Polonya", "Arnavutluk", "Turkiye", "Almanya", "Fransa", "Ingiltere", "Ispanya", "Italya",
    "Galler", "Iskoçya", "Irlanda", "Çekya", "Bosna Hersek", "Hırvatistan", "Sırbistan"
]

class FluidMatcher:
    """Advanced name matching engine for bridging diverse naming conventions."""
    
    COMMON_SUFFIXES = [
        ' fc', ' cf', ' sa', ' as', ' sports', ' city', ' club', ' fk', 
        ' sc', ' afc', ' 05', ' 1905', ' 1899', ' united', ' real', ' saint', 
        ' st', ' bk', ' if', ' sk', ' spor', ' fk', ' as', ' izmir', ' istanbul',
        ' hotspur', ' saint germain', ' saint-germain', ' sg', ' cum',
        ' munih', ' munchen', ' munich', ' bergamo'
    ]
    
    COMMON_PREFIXES = [
        'fc ', 'rc ', 'nk ', 'ac ', 'bc ', 'sc ', 'fk ', 'as ', 'ks ', 'real ', 
        'racing ', 'atletico ', 'sporting ', 'union ', 'clube ', 'de ', 'la ',
        'rayo ', 'osc ', 'fsv ', 'man ', 'psg '
    ]

    @staticmethod
    def simplify(text):
        """Deep normalization: lowercase, ascii, no punctuation, no common suffixes/prefixes."""
        if not text: return ""
        n = normalize_turkish(text).lower()
        # Remove punctuation
        for char in ".-&/()":
            n = n.replace(char, ' ')
        
        # Recursive suffix/prefix stripping
        changed = True
        while changed:
            changed = False
            # Suffixes
            for s in FluidMatcher.COMMON_SUFFIXES:
                if n.endswith(s):
                    n = n[:len(n)-len(s)].strip()
                    changed = True
            # Prefixes
            for p in FluidMatcher.COMMON_PREFIXES:
                if n.startswith(p):
                    n = n[len(p):].strip()
                    changed = True
        return " ".join(n.split())

    @staticmethod
    def get_sort_key(text):
        """Returns a string of sorted unique words for order-independent matching."""
        simplified = FluidMatcher.simplify(text)
        words = sorted(list(set(simplified.split())))
        return " ".join(words)

    @staticmethod
    def match(scraped_name, candidate_list, cutoff=0.85):
        """
        Multi-stage matching:
        1. Exact simplified match
        2. Sorted word match (Paris Saint German == Paris German Saint)
        3. High-precision fuzzy match
        """
        scrap_simple = FluidMatcher.simplify(scraped_name)
        scrap_sorted = FluidMatcher.get_sort_key(scraped_name)
        
        # Phase 1 & 2: Structural matches
        for cand in candidate_list:
            cand_simple = FluidMatcher.simplify(cand)
            if scrap_simple == cand_simple:
                return cand
            
            cand_sorted = FluidMatcher.get_sort_key(cand)
            if scrap_sorted == cand_sorted:
                return cand
        
        # Phase 3: Fuzzy fallback
        # We compare simplified versions for the fuzzy match to reduce noise
        cand_map = {FluidMatcher.simplify(c): c for c in candidate_list}
        matches = difflib.get_close_matches(scrap_simple, list(cand_map.keys()), n=1, cutoff=cutoff)
        if matches:
            return cand_map[matches[0]]
            
        return None

def get_canonical_name(scraped_name, database_names=[]):
    """
    Returns the canonical database name for a scraped name.
    """
    scraped_name = scraped_name.strip()
    
    # 1. Permanent Mappings (Hardcoded Master Registry)
    if scraped_name in MASTER_ALIAS_REGISTRY:
        return MASTER_ALIAS_REGISTRY[scraped_name]
    
    norm_scraped = normalize_turkish(scraped_name).lower()
    
    # 2. National Team check
    for nt in NATIONAL_TEAMS:
        if normalize_turkish(nt).lower() == norm_scraped:
            return scraped_name
    
    # 3. Use FluidMatcher for database search
    if database_names:
        matched = FluidMatcher.match(scraped_name, database_names)
        if matched:
            return matched
            
    return scraped_name # Fallback to original
