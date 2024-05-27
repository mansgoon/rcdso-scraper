import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor

# Setup Selenium WebDriver
def setup_driver():
    options = Options()
    options.add_argument('--ignore-certificate-errors')  # Ignore SSL certificate errors
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

# Define the base URL for scraping
base_url = "https://www.rcdso.org/find-a-dentist/search-results?Alpha=&City=Mississauga&MbrSpecialty=&ConstitID=&AlphaParent=&Address1=&PhoneNum=&SedationType=&SedationProviderType=&GroupCode=&DetailsCode="

def scrape_current_page(driver, dentists, limit):
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

            # Check for the specialty
            try:
                specialty = driver.find_element(By.XPATH, '//dt[text()="Specialty:"]/following-sibling::dd').text.strip()
                print(f"Specialty found for dentist: {name}, skipping...")
            except Exception:
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
            time.sleep(1)  # Ensure the previous page has loaded

        except Exception as e:
            print(f"Error parsing dentist entry: {e}")
            print(item.get_attribute('outerHTML'))

        if len(dentists) >= limit:
            break

    return True

def navigate_to_last_page(driver):
    while True:
        try:
            # Locate the last page button by finding the page link that comes after the ellipsis
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)  # Ensure the page scroll completes
            ellipsis = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//span[@class="page-link" and text()="..."]/parent::li/following-sibling::li/a'))
            )
            driver.execute_script("arguments[0].scrollIntoView();", ellipsis)
            time.sleep(1)
            ellipsis.click()
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row')))
            time.sleep(1)  # Ensure last page has loaded
            break
        except Exception as e:
            print(f"Error navigating to last page: {e}")
            break

def get_dentists(url, limit=50, reverse=False):
    driver = setup_driver()
    dentists = []

    print(f"Fetching data from URL: {url}")
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row')))
    time.sleep(1)  # Ensure page has loaded

    if reverse:
        # Navigate to the last page
        navigate_to_last_page(driver)

    while len(dentists) < limit:
        if not scrape_current_page(driver, dentists, limit):
            break

        if len(dentists) >= limit:
            break

        # Scroll to the bottom of the page to ensure the "Next" or "Previous" button is in view
        print("Scrolling to the bottom of the page")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Check if there's a "Next" or "Previous" button to load more results
        try:
            if reverse:
                button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//a[@class="page-link prev"]'))
                )
            else:
                button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//a[@class="page-link next"]'))
                )
            print(f"{button.text} button found. Clicking to reveal more results.")
            button.click()

            # Wait for the new set of results to be visible
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row'))
            )
            print("More results revealed. Continuing to scrape.")
        except Exception as e:
            print(f"No more results to reveal or error occurred: {e}")
            break

    driver.quit()
    return dentists

def remove_duplicates(dentists):
    unique_dentists = []
    seen = set()
    for dentist in dentists:
        dentist_tuple = tuple(dentist.items())
        if dentist_tuple not in seen:
            seen.add(dentist_tuple)
            unique_dentists.append(dentist)
    return unique_dentists

def main():
    test_url = base_url
    test_limit = 510

    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(get_dentists, test_url, test_limit, False)
        future2 = executor.submit(get_dentists, test_url, test_limit, True)

    dentists1 = future1.result()
    dentists2 = future2.result()

    # Combine results and remove duplicates
    all_dentists = remove_duplicates(dentists1 + dentists2)

    # Save the results to an Excel file
    df = pd.DataFrame(all_dentists)
    excel_file_path = 'dentists_in_mississauga2.xlsx'
    df.to_excel(excel_file_path, index=False)
    print(f"Data saved to {excel_file_path}")

if __name__ == "__main__":
    main()
