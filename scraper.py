import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Setup Selenium WebDriver
options = Options()
# options.headless = False  # Disable headless mode to see browser actions
options.add_argument('--ignore-certificate-errors')  # Ignore SSL certificate errors
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Define the base URL for scraping
base_url = "https://www.rcdso.org/find-a-dentist/search-results?Alpha=&City=Oakville&MbrSpecialty=&ConstitID=&AlphaParent=&Address1=&PhoneNum=&SedationType=&SedationProviderType=&GroupCode=&DetailsCode="

def scrape_current_page(dentists, limit):
    items = driver.find_elements(By.CSS_SELECTOR, 'div#dentistSearchResults .row')
    visible_items = [item for item in items if item.is_displayed()]
    print(f"Found {len(visible_items)} visible items on the current page.")
    
    if not visible_items:
        print("No visible dentist search results found.")
        return False

    for item in visible_items[:10]:  # Process 10 results at a time
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

            # Click on the name to go to the details page
            name_link = item.find_element(By.CSS_SELECTOR, 'h2 a')
            driver.execute_script("arguments[0].scrollIntoView();", name_link)
            time.sleep(1)
            try:
                name_link.click()
            except Exception as e:
                print(f"Click intercepted, retrying: {e}")
                driver.execute_script("arguments[0].click();", name_link)
            
            time.sleep(2)  # Ensure the details page has loaded

            # Check for the specialty
            try:
                specialty = driver.find_element(By.XPATH, '//dt[text()="Specialty:"]/following-sibling::dd').text.strip()
                print(f"Specialty found for dentist: {name}, skipping...")
            except Exception as e:
                # If no specialty is found, add the dentist to the list
                try:
                    zip_code = driver.find_element(By.XPATH, '//address//span[last()]').text.strip()
                    city = f"Mississauga ON {zip_code}"
                except Exception as zip_e:
                    city = "Mississauga"

                dentists.append({
                    'Name': name,
                    'Business Name': business_name,
                    'Address': address,
                    'City': city
                })
                print(f"Found dentist: {name}, {business_name}, {address}, {city}")

            # Go back to the previous page
            driver.back()
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row')))
            time.sleep(2)  # Ensure the previous page has loaded

        except Exception as e:
            print(f"Error parsing dentist entry: {e}")
            print(item.get_attribute('outerHTML'))

    return True

def get_dentists(url, limit=50):
    dentists = []

    print(f"Fetching data from URL: {url}")
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row')))
    time.sleep(2)  # Ensure page has loaded

    while len(dentists) < limit:
        if not scrape_current_page(dentists, limit):
            break

        # Scroll to the bottom of the page to ensure the "Next" button is in view
        print("Scrolling to the bottom of the page")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)  # Ensure the page scroll completes and wait a bit longer

        # Check if there's a "Next" button to load more results
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[@class="page-link next"]'))
            )
            print("Next button found. Clicking to reveal more results.")
            next_button.click()
            time.sleep(3)  # Ensure the next set of results is revealed

            # Wait for the new set of results to be visible
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row'))
            )
            print("More results revealed. Continuing to scrape.")
        except Exception as e:
            print(f"No more results to reveal or error occurred: {e}")
            break

    return dentists

# Test the function with a limit
test_url = base_url
test_limit = 50
test_dentists = get_dentists(test_url, test_limit)

# Save the results to an Excel file
# df = pd.DataFrame(test_dentists)
# excel_file_path = 'dentists_in_oakville.xlsx'
# df.to_excel(excel_file_path, index=False)
# print(f"Data saved to {excel_file_path}")

# Close the WebDriver
driver.quit()
