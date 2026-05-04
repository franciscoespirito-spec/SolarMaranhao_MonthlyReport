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

print(f"[{datetime.now()}] Iniciando Chrome")
driver = webdriver.Chrome(options=options)
print(f"[{datetime.now()}] Chrome OK")

try:
    driver.get("https://anonymousemail.me/")
    time.sleep(4)
    print(f"[{datetime.now()}] Site carregado")

    to = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "am-to")))
    driver.execute_script("arguments[0].value = arguments[1]", to, "compliance@beng.eng.br")
    time.sleep(1)
    print(f"[{datetime.now()}] To OK")

    subj = driver.find_element(By.NAME, "am-subject")
    driver.execute_script("arguments[0].value = arguments[1]", subj, test_label)
    time.sleep(1)
    print(f"[{datetime.now()}] Subject OK")

    print(f"[{datetime.now()}] Preenchendo Body")
    try:
        body = driver.find_element(By.NAME, "am-body")
        driver.execute_script("arguments[0].value = arguments[1]", body, test_label)
        print(f"[{datetime.now()}] Body OK")
    except:
        print(f"[{datetime.now()}] Body not found, skipping")
    
    time.sleep(2)

    print(f"[{datetime.now()}] Clicando botao")
    btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    driver.execute_script("arguments[0].click();", btn)
    time.sleep(5)
    print(f"[{datetime.now()}] SUCESSO!")

except Exception as e:
    print(f"[{datetime.now()}] ERRO: {e}")

finally:
    driver.quit()
