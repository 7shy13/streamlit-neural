"""
Debug v3: Find the full row structure with odds by going higher up the DOM tree.
The parent ul has only 4 children (fav, mbs, time, teamnames) - odds must be in a 
sibling or grandparent structure.
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json

URL = "https://www.iddaa.com/program/futbol?mbs=1"
UA  = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36"

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--log-level=3")
options.add_argument(f"user-agent={UA}")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    driver.get(URL)
    
    try:
        btn = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Tümünü Kabul') or contains(text(),'Kabul Et')]"))
        )
        btn.click()
        time.sleep(1)
    except:
        pass
    
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='i_tnw__t8AmC']"))
        )
    except:
        pass
    time.sleep(3)

    # Get the grandparent (2 levels up) of the first team names element
    result = driver.execute_script("""
        var teamEl = document.querySelector('[class*="i_tnw__t8AmC"]');
        if (!teamEl) return 'NOT FOUND';
        
        var gp1 = teamEl.parentElement; // ul.i_md__vix_N
        var gp2 = gp1?.parentElement;   // ?
        var gp3 = gp2?.parentElement;   // ?
        
        return {
            gp1Tag: gp1?.tagName,
            gp1Class: gp1?.className,
            gp1ChildCount: gp1?.children?.length,
            gp2Tag: gp2?.tagName,
            gp2Class: gp2?.className,
            gp2ChildCount: gp2?.children?.length,
            gp2HTML: gp2?.innerHTML?.substring(0, 3000),
            gp3Tag: gp3?.tagName,
            gp3Class: gp3?.className,
            gp3ChildCount: gp3?.children?.length,
        };
    """)
    print("DOM TREE ANALYSIS:")
    print(json.dumps(result, indent=2, ensure_ascii=False)[:5000])
    
    # Also try to find all numeric elements (odds) on the page
    all_odds_els = driver.execute_script("""
        // Find all elements that contain only decimal numbers (odds pattern)
        var all = document.querySelectorAll('button, span, li, div');
        var oddEls = [];
        for(var i=0; i<all.length; i++) {
            var text = all[i].textContent.trim();
            if(/^\\d\\.\\d{2}$/.test(text) && all[i].children.length === 0) {
                oddEls.push({
                    tag: all[i].tagName,
                    cls: all[i].className.substring(0, 80),
                    text: text,
                    parentTag: all[i].parentElement?.tagName,
                    parentClass: all[i].parentElement?.className.substring(0, 80)
                });
            }
        }
        return oddEls.slice(0, 30);
    """)
    print("\n\nODDS ELEMENTS FOUND:")
    print(json.dumps(all_odds_els, indent=2, ensure_ascii=False)[:5000])

finally:
    driver.quit()
