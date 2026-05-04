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

driver = webdriver.Chrome(options=options)
driver.get("https://anonymousemail.me/")
time.sleep(4)

to = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "am-to")))
to.clear()
to.send_keys("compliance@beng.eng.br")
time.sleep(1)

subj = driver.find_element(By.NAME, "am-subject")
subj.clear()
subj.send_keys(test_label)
time.sleep(1)

try:
    body = driver.find_element(By.NAME, "am-body")
except:
    body = driver.find_element(By.CSS_SELECTOR, "textarea")
body.clear()
body.send_keys(test_label)
time.sleep(2)

btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
btn.click()
time.sleep(5)

print("SUCESSO!")
driver.quit()
