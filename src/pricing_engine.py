import numpy as np
from scipy.stats import poisson

def bivariate_poisson_prob(x, y, lambda_x, lambda_y, rho):
    """
    Dixon-Coles uyarlamalı Bivariate Poisson olasılık fonksiyonu.
    x: Ev sahibi golü, y: Deplasman golü
    lambda_x: Ev sahibi gol beklentisi (Contextual Alpha uygulanmış)
    lambda_y: Deplasman gol beklentisi (Contextual Alpha uygulanmış)
    rho: Dixon-Coles bağımlılık parametresi (0.0087 gibi 0'a yakın pozitif bir değer)
    """
    # Bağımsız Poisson olasılıkları
    prob_indep = poisson.pmf(x, lambda_x) * poisson.pmf(y, lambda_y)
    
    # Düşük skorlardaki beraberlikleri ve 1 farklı galibiyetleri dengeleyen Dixon-Coles düzeltmesi
    tau = 1.0
    if x == 0 and y == 0:
        tau = 1 - (lambda_x * lambda_y * rho)
    elif x == 0 and y == 1:
        tau = 1 + (lambda_x * rho)
    elif x == 1 and y == 0:
        tau = 1 + (lambda_y * rho)
    elif x == 1 and y == 1:
        tau = 1 - rho
        
    return max(0, prob_indep * tau) # Olasılık < 0 olamaz

def calculate_1x2_probs(lambda_h, lambda_a, rho, max_goals=10):
    """
    Bivariate Poisson matrisi üzerinden 1, X, 2 tam zamanlı olasılıklarını hesaplar.
    """
    prob_home = 0.0
    prob_draw = 0.0
    prob_away = 0.0
    
    for i in range(max_goals):
        for j in range(max_goals):
            p = bivariate_poisson_prob(i, j, lambda_h, lambda_a, rho)
            if i > j:
                prob_home += p
            elif i == j:
                prob_draw += p
            else:
                prob_away += p
                
    # Normalize et (matris 10'da kesildiği için ufak kayıplar olabilir)
    total = prob_home + prob_draw + prob_away
    return prob_home/total, prob_draw/total, prob_away/total

def calculate_asian_handicap_fair_odds(lambda_h, lambda_a, rho, handicap=-0.5, max_goals=10):
    """
    Belirli bir Asya Handikapı (AH) çizgisi için 'Adil Oranları' (Fair Odds) üretir.
    handicap: Ev sahibi için handikap çizgisi. Örn: -0.5, -0.25, 0.0
    """
    prob_home_cover = 0.0
    prob_away_cover = 0.0
    prob_push = 0.0 # İade olma durumu (AH 0, AH -1 vb. tam sayılarda)
    
    for i in range(max_goals):
        for j in range(max_goals):
            p = bivariate_poisson_prob(i, j, lambda_h, lambda_a, rho)
            
            # Handikaplı skoru hesapla
            net_score = (i + handicap) - j
            
            if net_score > 0:
                prob_home_cover += p
            elif net_score < 0:
                prob_away_cover += p
            else:
                prob_push += p
                
    # Çeyrekli (Quarter) Handikaplar (-0.25, -0.75) için Push olmaz, 
    # Half-Win / Half-Loss durumları bahis kuponunda çözülür. 
    # Fiyatlandırma motoru sadece çizgiyi geçme olasılığını verir.
    
    # Push olasılığını dışarıda bırakıp efektif oran bulma (Vigorish olmadan Fair Odds)
    effective_total = prob_home_cover + prob_away_cover
    
    if effective_total == 0:
         return 0.0, 0.0
        
    fair_odds_home = 1.0 / (prob_home_cover / effective_total)
    fair_odds_away = 1.0 / (prob_away_cover / effective_total)
    
    return fair_odds_home, fair_odds_away
    
def pricing_engine_pipeline(lambda_h_base, lambda_a_base, context_dict, rho=0.0087):
    """
    Faz 1 ve Faz 2 parametrelerini alır, nihai Contextual Lambda'ları üretir
    ve piyasa yapıcı için Pricing objesi döndürür.
    
    context_dict örnek:
    {
        'home_delta_xt': 0.15, 'home_fatigue_gamma': 0.92, 'home_motivation_m': 1.05,
        'away_delta_xt': 0.0, 'away_fatigue_gamma': 1.0, 'away_motivation_m': 0.98
    }
    """
    from player_impact import calculate_player_impact
    from schedule_fatigue import calculate_fatigue_penalty
    
    # 1. Player Impact İskontosu
    lambda_h_adj = calculate_player_impact(lambda_h_base, context_dict.get('home_delta_xt', 0))
    lambda_a_adj = calculate_player_impact(lambda_a_base, context_dict.get('away_delta_xt', 0))
    
    # 2. Fatigue (Yorgunluk) ve Motivasyon İskontosu 
    # Not: Gerçek modelde decay_gamma hesaplanmış olarak context'ten gelir
    lambda_h_final = lambda_h_adj * context_dict.get('home_fatigue_gamma', 1.0) * context_dict.get('home_motivation_m', 1.0)
    lambda_a_final = lambda_a_adj * context_dict.get('away_fatigue_gamma', 1.0) * context_dict.get('away_motivation_m', 1.0)
    
    # Olasılıkları Çıkar
    p_1, p_x, p_2 = calculate_1x2_probs(lambda_h_final, lambda_a_final, rho)
    ah_home, ah_away = calculate_asian_handicap_fair_odds(lambda_h_final, lambda_a_final, rho, handicap=-0.5)
    
    return {
        'Adj_Lambda_H': lambda_h_final,
        'Adj_Lambda_A': lambda_a_final,
        'Fair_1': 1/p_1, 'Fair_X': 1/p_x, 'Fair_2': 1/p_2,
        'Fair_AH_Minus_0_5': ah_home,
        'Fair_AH_Plus_0_5': ah_away
    }
