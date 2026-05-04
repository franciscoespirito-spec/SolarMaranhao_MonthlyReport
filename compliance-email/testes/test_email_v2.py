import sys, time
from datetime import datetime

now = datetime.now()
test_label = f"Teste_{now.year}_{now.month:02d}"
print(f"[{datetime.now()}] Label: {test_label}")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--remote-debugging-port=9222')

print(f"[{datetime.now()}] Iniciando Chrome")
driver = webdriver.Chrome(options=options)
print(f"[{datetime.now()}] Chrome OK")

driver.get("https://anonymousemail.me/")
time.sleep(4)
print(f"[{datetime.now()}] Site carregado")

to = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "am-to")))
to.clear()
to.send_keys("compliance@beng.eng.br")
time.sleep(1)
print(f"[{datetime.now()}] To OK")

subj = driver.find_element(By.NAME, "am-subject")
subj.clear()
subj.send_keys(test_label)
time.sleep(1)
print(f"[{datetime.now()}] Subject OK")

try:
    body = driver.find_element(By.NAME, "am-body")
except:
    body = driver.find_element(By.CSS_SELECTOR, "textarea")
body.clear()
body.send_keys(test_label)
time.sleep(2)
print(f"[{datetime.now()}] Body OK")

btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
btn.click()
time.sleep(5)

print(f"[{datetime.now()}] SUCESSO!")
driver.quit()
