import psycopg2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import openpyxl
import re

chrome_options = Options()
chrome_options.add_argument("--start-maximized")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
wait = WebDriverWait(driver, 10)

conn = psycopg2.connect(
    host="localhost",
    database="database automation",
    user="postgres",
    password="root",
    port="5432"
)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS Job_data (
    company_name TEXT,
    job_title TEXT,
    salary NUMERIC,
    location TEXT
)
""")
conn.commit()

def extract_salary_value(salary_str):
    if not salary_str or not isinstance(salary_str, str):
        return None
    
    nums = re.findall(r'\d[\d,]*', salary_str)
    if not nums:
        return None

    last = nums[-1].replace(',', '')   
    try:
        return int(last)
    except ValueError:
        return None

driver.get("https://in.indeed.com/")
time.sleep(2)

driver.find_element(By.ID, "text-input-what").send_keys("fresher")
driver.find_element(By.ID, "text-input-where").clear()
driver.find_element(By.ID, "text-input-where").send_keys("delhi")
driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.job_seen_beacon")))
time.sleep(2)  
results = []
job_cards_count = len(driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon"))
print("Found job cards:", job_cards_count)

for i in range(job_cards_count):
    cards = driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")
    card = cards[i]
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
    time.sleep(0.5)
    try:
        comps = card.find_elements(By.CSS_SELECTOR, "span[data-testid='company-name']")
        company = comps[-1].text.strip() if comps else "N/A"
    except Exception:
        company = "N/A"
    try:
        job_title = card.find_element(By.CSS_SELECTOR, "h2.jobTitle span").text.strip()
    except Exception:
        job_title = "N/A"
    try:
        location = card.find_element(By.CSS_SELECTOR, "div[data-testid='text-location']").text.strip()
    except:
        try:
            location = card.find_element(By.CSS_SELECTOR, "div.company_location").text.strip()
        except:
            location = "N/A"

    salary = "N/A"
    salary_selectors = [
        "div.salary-snippet-container",
        "span[data-testid='attribute_snippet_testid']",
        "li.metadata.salary-snippet-container div"
    ]
    for sel in salary_selectors:
        try:
            elem = card.find_element(By.CSS_SELECTOR, sel)
            text = elem.text.strip()
            if text:
                salary = text
                break
        except:
            continue
    
    salary=extract_salary_value(salary)
    cur.execute("""
        INSERT INTO Job_data (company_name, job_title, salary, location)
        VALUES (%s, %s, %s, %s)
    """, (company, job_title, salary, location))
    conn.commit()

cur.execute("SELECT job_title, location, AVG(salary) FROM Job_data  GROUP BY location, job_title ORDER BY location;")
rows = cur.fetchall()

for row in rows:
    print(f"Job Title: {row[0]}, Location: {row[1]}, Average Salary: {row[2]}")

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Job Salary Data"
headers = ["Job Title", "Location", "Average Salary"]
ws.append(headers)
for row in rows:
    ws.append(row)
excel_file = "job_salary_data.xlsx"
wb.save(excel_file)
print(f"Data saved successfully in '{excel_file}'")

driver.quit()
cur.close()
conn.close()