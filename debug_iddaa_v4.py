"""
Debug v4: Exhaustive class inspection within i_mc__MDEbN containers.
This will help us see if class names have shifted.
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
    
    # Wait for content
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='i_mc__']"))
        )
    except:
        pass
    time.sleep(5)

    result = driver.execute_script("""
        var containers = document.querySelectorAll('[class*="i_mc__"]');
        if (containers.length === 0) return { error: 'No i_mc__ containers found' };
        
        var debugRows = [];
        for (var i=0; i < Math.min(containers.length, 5); i++) {
            var c = containers[i];
            var allHtml = c.innerHTML;
            var classes = Array.from(c.querySelectorAll('*')).map(el => el.className).filter(cl => cl);
            var spansWithTitle = Array.from(c.querySelectorAll('span[title]')).map(s => s.getAttribute('title'));
            
            debugRows.push({
                index: i,
                ownClass: c.className,
                childCount: c.children.length,
                internalClasses: classes.slice(0, 20),
                spansWithTitle: spansWithTitle,
                fullText: c.textContent.trim().substring(0, 200)
            });
        }
        return { count: containers.length, rows: debugRows };
    """)
    
    print("DOM INSPECTION RESULT:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

finally:
    driver.quit()
