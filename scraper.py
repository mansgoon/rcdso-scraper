import sys
import time
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLineEdit, QLabel, QTextEdit, QFrame, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer, QElapsedTimer
from PyQt5.QtGui import QFont, QPalette, QColor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor
import os
import random

# Define the base URL for scraping
base_url = "https://www.rcdso.org/find-a-dentist/search-results?Alpha=&City={}&MbrSpecialty=&ConstitID=&AlphaParent=&Address1=&PhoneNum=&SedationType=&SedationProviderType=&GroupCode=&DetailsCode="

# Setup Selenium WebDriver
def setup_driver():
    options = Options()
    options.add_argument('--ignore-certificate-errors')  # Ignore SSL certificate errors
    
    # Get the path to the ChromeDriver executable
    chrome_driver_path = ChromeDriverManager().install()
    
    # Ensure we're using the correct executable
    if chrome_driver_path.endswith('THIRD_PARTY_NOTICES.chromedriver'):
        chrome_driver_path = os.path.dirname(chrome_driver_path)
        chrome_driver_path = os.path.join(chrome_driver_path, 'chromedriver.exe')
    
    # Print the path for debugging
    print(f"ChromeDriver path: {chrome_driver_path}")
    
    # Check if the file exists
    if not os.path.exists(chrome_driver_path):
        raise FileNotFoundError(f"ChromeDriver not found at {chrome_driver_path}")
    
    # Create the Service object with the ChromeDriver path
    service = Service(chrome_driver_path)
    
    # Create the driver with the service and options
    driver = webdriver.Chrome(service=service, options=options)
    
    return driver

def scrape_current_page(driver, dentists, limit, search_city, sedation_check, update_status):
    items = driver.find_elements(By.CSS_SELECTOR, 'div#dentistSearchResults .row')
    visible_items = [item for item in items if item.is_displayed()]
    update_status.emit(f"Found {len(visible_items)} visible items on the current page.")
    
    if not visible_items:
        update_status.emit("No visible dentist search results found.")
        return False

    for item in visible_items[:10]:  # Process 10 results at a time
        if len(dentists) >= limit:
            return False

        try:
            name = item.find_element(By.CSS_SELECTOR, 'h2').text.strip()

            # Click on the name to go to the details page
            name_link = item.find_element(By.CSS_SELECTOR, 'h2 a')
            driver.execute_script("arguments[0].scrollIntoView();", name_link)
            time.sleep(1)
            try:
                name_link.click()
            except Exception as e:
                update_status.emit(f"Click intercepted, retrying: {e}")
                driver.execute_script("arguments[0].click();", name_link)

            # Check for the specialty
            try:
                specialty = driver.find_element(By.XPATH, '//dt[text()="Specialty:"]/following-sibling::dd').text.strip()
                update_status.emit(f"Specialty found for dentist: {name}, skipping...")
                driver.back()
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row')))
                time.sleep(1)  # Ensure the previous page has loaded
                continue
            except Exception:
                pass

            # Check for the "Primary Practice" section
            try:
                driver.find_element(By.XPATH, '//h3[text()="Primary Practice"]')
            except Exception as e:
                update_status.emit(f"No Primary Practice section for dentist: {name}, skipping...")
                driver.back()
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row')))
                time.sleep(1)  # Ensure the previous page has loaded
                continue

            # Check for the "View Facility Permits" link
            try:
                permit_link = driver.find_element(By.LINK_TEXT, 'View Facility Permits')
                driver.execute_script("arguments[0].scrollIntoView();", permit_link)
                time.sleep(1)
                try:
                    permit_link.click()
                except Exception as e:
                    update_status.emit(f"Click intercepted, retrying: {e}")
                    driver.execute_script("arguments[0].click();", permit_link)

                # Check the sedation type
                try:
                    sedation_type_element = driver.find_element(By.XPATH, '//dt[contains(text(), "Highest Level Of Sedation")]/following-sibling::dd')
                    sedation_type = sedation_type_element.text.strip()
                    update_status.emit(f"Sedation type found for dentist {name}: {sedation_type}")
                    if sedation_check not in sedation_type:
                        update_status.emit(f"Sedation type {sedation_type} does not contain {sedation_check}, skipping...")
                        driver.back()
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistDetails')))
                        time.sleep(1)  # Ensure the previous page has loaded
                        driver.back()
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row')))
                        time.sleep(1)  # Ensure the previous page has loaded
                        continue
                except Exception as e:
                    update_status.emit(f"No sedation type found for dentist: {name}, skipping... {e}")
                    driver.back()
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistDetails')))
                    time.sleep(1)  # Ensure the previous page has loaded
                    driver.back()
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row')))
                    time.sleep(1)  # Ensure the previous page has loaded
                    continue

                driver.back()
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistDetails')))
                time.sleep(1)  # Ensure the previous page has loaded
            except Exception:
                # No need to print anything if the link is not found
                pass

            # Click on the "See All Practice Locations" link
            try:
                expand_link = driver.find_element(By.XPATH, '//a[@data-collapsible-toggle]')
                driver.execute_script("arguments[0].click();", expand_link)
                time.sleep(1)  # Ensure the section expands
            except Exception as e:
                update_status.emit(f"Error expanding practice locations: {e}")

            # Extract details from all practice locations
            locations = driver.find_elements(By.CSS_SELECTOR, 'div[data-collapsible-toggled] .row')
            for location in locations:
                try:
                    try:
                        business_name = location.find_element(By.CSS_SELECTOR, 'h6').text.strip()
                    except Exception:
                        business_name = ''

                    address_tag = location.find_element(By.CSS_SELECTOR, 'address')
                    spans = address_tag.find_elements(By.TAG_NAME, 'span')
                    if len(spans) >= 3:
                        address = spans[0].text.strip()
                        city_state_zip = spans[1].text.strip().replace(',', '')
                        zip_code = spans[2].text.strip()
                        city = f"{search_city} ON {zip_code}"
                        if search_city.lower() not in city_state_zip.lower():
                            continue  # Skip locations not matching the search city
                    else:
                        address = ''
                        zip_code = ''
                        city = ''

                    dentists.append({
                        'Name': name,
                        'Business Name': business_name,
                        'Address': address,
                        'City': city
                    })
                    update_status.emit(f"Found dentist: {name}, {business_name}, {address}, {city}")
                except Exception as e:
                    update_status.emit(f"Error extracting location details: {e}")

            # Go back to the previous page
            driver.back()
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row')))
            time.sleep(1)  # Ensure the previous page has loaded

        except Exception as e:
            update_status.emit(f"Error parsing dentist entry: {e}")
            update_status.emit(item.get_attribute('outerHTML'))

        if len(dentists) >= limit:
            break

    return True

def navigate_to_last_page(driver, update_status):
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
            update_status.emit(f"Error navigating to last page: {e}")
            break

def get_dentists(url, limit, reverse, search_city, sedation_check, update_status, update_progress):
    driver = setup_driver()
    dentists = []

    update_status.emit(f"Fetching data from URL: {url}")
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row')))
    time.sleep(1)  # Ensure page has loaded

    if reverse:
        # Navigate to the last page
        navigate_to_last_page(driver, update_status)

    while len(dentists) < limit:
        if not scrape_current_page(driver, dentists, limit, search_city, sedation_check, update_status):
            break

        # Update progress based on the number of dentists scraped
        update_progress.emit(len(dentists))

        if len(dentists) >= limit:
            break

        # Scroll to the bottom of the page to ensure the "Next" or "Previous" button is in view
        update_status.emit("Scrolling to the bottom of the page")
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
            update_status.emit(f"{button.text} button found. Clicking to reveal more results.")
            button.click()

            # Wait for the new set of results to be visible
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div#dentistSearchResults .row'))
            )
            update_status.emit("More results revealed. Continuing to scrape.")
        except Exception as e:
            update_status.emit(f"No more results to reveal or error occurred: {e}")
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

class ScraperThread(QThread):
    update_progress = pyqtSignal(int)
    update_status = pyqtSignal(str)
    scraping_finished = pyqtSignal(list)

    def __init__(self, url, limit, reverse, search_city, sedation_check):
        QThread.__init__(self)
        self.url = url
        self.limit = limit
        self.reverse = reverse
        self.search_city = search_city
        self.sedation_check = sedation_check

    def run(self):
        dentists = get_dentists(self.url, self.limit, self.reverse, self.search_city, self.sedation_check, self.update_status, self.update_progress)
        self.scraping_finished.emit(dentists)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RCDSO Scraper")
        self.setGeometry(100, 100, 600, 500)  # Reduced window size
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QLabel { color: #e0e0e0; font-size: 12px; }
            QLineEdit {
                background-color: #3b3b3b; border: 1px solid #555555;
                border-radius: 3px; color: #e0e0e0; padding: 3px;
                font-size: 12px;
            }
            QPushButton {
                background-color: #4a4a4a; color: #e0e0e0; border: none;
                border-radius: 3px; padding: 5px; font-size: 12px;
            }
            QPushButton:hover { background-color: #5a5a5a; }
            QTextEdit {
                background-color: #3b3b3b; color: #e0e0e0;
                border: 1px solid #555555; border-radius: 3px; font-size: 12px;
            }
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #4a4a4a;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)  # Reduced spacing
        main_layout.setContentsMargins(10, 10, 10, 10)  # Reduced margins
        main_widget.setLayout(main_layout)

        # Title
        title_label = QLabel("RCDSO Scraper")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        # Input fields
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: #333333; border-radius: 5px; padding: 15px;")
        input_layout = QVBoxLayout()
        input_layout.setSpacing(15)  # Increased spacing between inputs
        input_frame.setLayout(input_layout)

        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("Enter city (e.g., Etobicoke)")
        self.sedation_input = QLineEdit()
        self.sedation_input.setPlaceholderText("Enter sedation type")
        self.limit_input = QLineEdit()
        self.limit_input.setPlaceholderText("Enter limit (e.g., 150)")

        input_layout.addLayout(self.create_input_field("City:", self.city_input))
        input_layout.addLayout(self.create_input_field("Sedation:", self.sedation_input))
        input_layout.addLayout(self.create_input_field("Limit:", self.limit_input))

        main_layout.addWidget(input_frame)

        # Start button
        self.start_button = QPushButton("Start Scraping")
        self.start_button.clicked.connect(self.start_scraping)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #3daee9;
                color: #ffffff;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4dbefa;
            }
            QPushButton:pressed {
                background-color: #3193c9;
                color: #e0e0e0;
            }
        """)
        main_layout.addWidget(self.start_button)

        # Progress bar
        self.progress_container = QFrame()
        self.progress_container.setStyleSheet("""
            QFrame {
                background-color: #333333;
                border-radius: 9999px;
            }
        """)
        self.progress_container.setFixedHeight(8)
        main_layout.addWidget(self.progress_container)

        self.progress_bar = QFrame(self.progress_container)
        self.progress_bar.setStyleSheet("""
            QFrame {
                background-color: #48bb78;
                border-radius: 9999px;
            }
        """)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setFixedWidth(0)

        # Add a new attribute to track the progress
        self.progress = 0

        # Status text
        status_label = QLabel("Status:")
        main_layout.addWidget(status_label)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet("""
            padding: 5px;
            background-color: #3b3b3b;
            color: #e0e0e0;
            border: 1px solid #555555;
            border-radius: 3px;
            font-size: 12px;
        """)

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.status_text)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none;")
        main_layout.addWidget(scroll_area)

        self.all_dentists = []

    def create_input_field(self, label_text, input_widget):
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        label = QLabel(label_text)
        label.setFixedWidth(100)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        layout.addWidget(label)
        layout.addWidget(input_widget)
        layout.setStretchFactor(label, 0)
        layout.setStretchFactor(input_widget, 1)
        
        return layout

    def start_scraping(self):
        search_city = self.city_input.text().strip()
        sedation_check = self.sedation_input.text().strip()
        limit_text = self.limit_input.text().strip()

        # Check if any field is empty
        if not search_city or not sedation_check or not limit_text:
            self.update_status('<span style="color: #ff0000;">Error: All fields must be filled. Please provide City, Sedation type, and Limit.</span>')
            return

        try:
            limit = int(limit_text)
            if limit <= 0:
                raise ValueError("Limit must be a positive integer")
        except ValueError:
            self.update_status('<span style="color: #ff0000;">Error: Limit must be a valid positive integer.</span>')
            return

        url = base_url.format(search_city)

        self.thread1 = ScraperThread(url, limit // 2, False, search_city, sedation_check)
        self.thread2 = ScraperThread(url, limit // 2, True, search_city, sedation_check)

        self.thread1.update_status.connect(self.update_status)
        self.thread2.update_status.connect(self.update_status)
        self.thread1.update_progress.connect(self.update_progress)
        self.thread2.update_progress.connect(self.update_progress)
        self.thread1.scraping_finished.connect(self.handle_results)
        self.thread2.scraping_finished.connect(self.handle_results)

        self.all_dentists = []
        self.threads_finished = 0
        self.total_progress = 0
        self.total_limit = limit

        self.progress = 0
        self.progress_bar.setFixedWidth(0)
        self.start_controlled_progress()

        self.thread1.start()
        self.thread2.start()

        self.update_status('Scraping started...')

    def start_controlled_progress(self):
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_controlled_progress)
        self.progress_timer.start(100)  # Update every 100ms

    def update_controlled_progress(self):
        if self.threads_finished < 2:
            # Slowly increase progress up to 95% while threads are running
            self.progress = min(self.progress + 0.1, 95)
            width = int(self.progress_container.width() * (self.progress / 100))
            self.progress_bar.setFixedWidth(width)
        else:
            # Both threads finished, set to 100%
            self.progress_bar.setFixedWidth(self.progress_container.width())
            self.progress_timer.stop()

    def update_status(self, status):
        self.status_text.append(status)

    def update_progress(self, value):
        self.total_progress += value
        progress_percentage = min(self.total_progress / self.total_limit, 1)
        width = int(self.progress_container.width() * progress_percentage)
        self.progress_bar.setFixedWidth(width)

    def handle_results(self, dentists):
        self.all_dentists.extend(dentists)
        self.threads_finished += 1

        if self.threads_finished == 2:
            # Both threads have finished
            unique_dentists = remove_duplicates(self.all_dentists)
            self.save_results(unique_dentists)
            
            # Ensure progress bar is at 100%
            self.progress_bar.setFixedWidth(self.progress_container.width())
            self.progress_timer.stop()

    def save_results(self, dentists):
        df = pd.DataFrame(dentists)
        excel_file_path = f'dentists_in_{self.city_input.text()}_filtered.xlsx'
        df.to_excel(excel_file_path, index=False)
        self.update_status(f'<span style="color: #00ff00;">Data saved to {excel_file_path}</span>')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())