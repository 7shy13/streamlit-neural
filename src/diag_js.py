"""
Diagnostic script v2 for iddaa_scraper.py JS_EXTRACTOR.
This version logs more info and returns a status object.
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

JS_EXTRACTOR = r"""
(function() {
    try {
        var results = [];
        var containers = document.querySelectorAll('[class*="i_mc__"]');
        var logs = ["Containers: " + containers.length];
        
        for (var i=0; i < containers.length; i++) {
            var c = containers[i];
            var teamWrapper = c.querySelector('[class*="i_tnw__"]');
            if (!teamWrapper) {
                if(i < 2) logs.push("Row " + i + ": No teamWrapper");
                continue;
            }
            
            var spans = teamWrapper.querySelectorAll('span');
            if (spans.length < 2) {
                if(i < 2) logs.push("Row " + i + ": Spans < 2");
                continue;
            }
            
            var home = spans[0].getAttribute('title') || spans[0].textContent.trim();
            var away = spans[1].getAttribute('title') || spans[1].textContent.trim();
            
            var o1 = 0, oX = 0, o2 = 0;
            var lists = c.querySelectorAll('ul');
            for(var k=0; k < lists.length; k++) {
                var lis = lists[k].querySelectorAll('li');
                var nums = [];
                for(var j=0; j < lis.length; j++) {
                    var t = lis[j].textContent.trim();
                    if(/^\d+\.\d+$/.test(t)) nums.push(parseFloat(t));
                }
                if (nums.length === 3) {
                    o1 = nums[0]; oX = nums[1]; o2 = nums[2];
                    break;
                }
            }
            
            results.push({h: home, a: away, odds: [o1, oX, o2]});
        }
        return { success: true, count: results.length, data: results, logs: logs };
    } catch (e) {
        return { success: false, error: e.message, stack: e.stack };
    }
})();
"""

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
    print("Page loading...")
    time.sleep(10) # Heavy React wait
    
    print("Executing JS...")
    result = driver.execute_script("return " + JS_EXTRACTOR)
    print("RESULT:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

finally:
    driver.quit()
