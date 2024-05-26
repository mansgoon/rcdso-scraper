import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

options = Options()
# options.headless = False  # Disable headless mode to see browser actions
options.add_argument('--ignore-certificate-errors')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# define the base URL for scraping
base_url = "https://www.rcdso.org/find-a-dentist/search-results?Alpha=&City=Oakville&MbrSpecialty=&ConstitID=&AlphaParent=&Address1=&PhoneNum=&SedationType=&SedationProviderType=&GroupCode=&DetailsCode="

def scrape_current_page(dentists, limit):
    items = driver.find_elements(By.CSS_SELECTOR, 'div#dentistSearchResults .row')
    visible_items = [item for item in items if item.is_displayed()]
    print(f"Found {len(visible_items)} visible items on the current page.")
    
    if not visible_items:
        print("No visible dentist search results found.")
        return False

    for item in visible_items[:10]:  # process 10 results at a time
        if len(dentists) >= limit:
            return False

        try:
            name = item.find_element(By.CSS_SELECTOR, 'h2').text.strip()
            address_tag = item.find_element(By.CSS_SELECTOR, 'address')
            spans = address_tag.find_elements(By.TAG_NAME, 'span')
            if len(spans) >= 2:
                business_name = spans[0].text.strip()
                address = spans[1].text.strip()
            else:
                business_name = ''
                address = ''

            dentists.append({
                'Name': name,
                'Business Name': business_name,
                'Address': address,
                'City': 'Brampton'
            })

            # change city accordingly to the city you are scraping
            print(f"Found dentist: {name}, {business_name}, {address}, Brampton")

        except Exception as e:
            print(f"Error parsing dentist entry: {e}")
            print(item.get_attribute('outerHTML'))

    return True

def get_dentists(url, limit=50):
    dentists = []

    print(f"Fetching data from URL: {url}")
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row')))
    time.sleep(2)

    while len(dentists) < limit:
        if not scrape_current_page(dentists, limit):
            break

        print("Scrolling to the bottom of the page")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1) 

        # check if there's a "Next" button to load more results
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[@class="page-link next"]'))
            )
            print("Next button found. Clicking to reveal more results.")
            next_button.click()

            # wait for the new set of results to be visible
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row'))
            )
            print("More results revealed. Continuing to scrape.")
        except Exception as e:
            print(f"No more results to reveal or error occurred: {e}")
            break

    return dentists

test_url = base_url
test_limit = 1100
test_dentists = get_dentists(test_url, test_limit)

# save the results to an excel file
df = pd.DataFrame(test_dentists)
excel_file_path = 'dentists_in_oakville.xlsx'
df.to_excel(excel_file_path, index=False)
print(f"Data saved to {excel_file_path}")

driver.quit()
