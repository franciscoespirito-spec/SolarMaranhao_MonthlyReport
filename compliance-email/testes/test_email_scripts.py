#!/usr/bin/env python3
import sys
import time
from datetime import datetime

now = datetime.now()
test_label = f"Teste_{now.year}_{now.month:02d}"

print(f"[{datetime.now()}] Iniciando teste de email")
print(f"[{datetime.now()}] Label: {test_label}")

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    print(f"[{datetime.now()}] Selenium OK")
except:
    print(f"[{datetime.now()}] ERRO: Selenium nao importado")
    sys.exit(1)

try:
    print(f"[{datetime.now()}] Iniciando Chrome")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    print(f"[{datetime.now()}] Chrome OK")
    
    print(f"[{datetime.now()}] Acessando site")
    driver.get("https://anonymousemail.me/")
    time.sleep(4)
    print(f"[{datetime.now()}] Site carregado")
    
    print(f"[{datetime.now()}] Preenchendo To")
    to = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "am-to")))
    to.clear()
    to.send_keys("compliance@beng.eng.br")
    time.sleep(1)
    
    print(f"[{datetime.now()}] Preenchendo Subject")
    subj = driver.find_element(By.NAME, "am-subject")
    subj.clear()
    subj.send_keys(test_label)
    time.sleep(1)
    
    print(f"[{datetime.now()}] Preenchendo Body")
    try:
        body = driver.find_element(By.NAME, "am-body")
    except:
        body = driver.find_element(By.CSS_SELECTOR, "textarea")
    body.clear()
    body.send_keys(test_label)
    time.sleep(2)
    
    print(f"[{datetime.now()}] Clicando botao")
    try:
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    except:
        btn = driver.find_element(By.CSS_SELECTOR, "button")
    btn.click()
    time.sleep(5)
    
    print(f"[{datetime.now()}] SUCESSO!")
    driver.quit()
    
except Exception as e:
    print(f"[{datetime.now()}] ERRO: {e}")
    try:
        driver.quit()
    except:
        pass
    sys.exit(1)
