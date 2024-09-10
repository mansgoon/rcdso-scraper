# RCDSO Dental Office Scraper

This Python application scrapes dentist information from the Royal College of Dental Surgeons of Ontario (RCDSO) website. It uses Selenium with Chrome WebDriver to automate the browsing and extraction of data, and provides a graphical user interface (GUI) for easy interaction.


<p align="center" width="100%">
  <img width="40%" src="https://github.com/user-attachments/assets/6d4bd810-3a7c-4ead-8452-3376b4691122" />
</p>


## Features

- Scrapes dentist information including name, business name, address, and city
- Filters results based on sedation type
- Handles pagination to scrape multiple pages of results
- Saves the scraped data to an Excel file
- User-friendly GUI for inputting search parameters and viewing progress
- Concurrent scraping using two threads for improved performance

## Requirements

- Python 3.x
- PyQt5
- Selenium
- pandas
- webdriver_manager
- ChromeDriver (automatically managed by webdriver_manager)

## Installation

1. Clone the repository:
   ```git clone https://github.com/yourusername/rcdso-scraper.git```
   ```cd rcdso-scraper```

2. Install the required dependencies:
   ```pip install -r requirements.txt```


## Usage

1. Run the script:
   ```python scraper.py```

2. The GUI will open. Enter the following information:
   - City: The city to search for dentists (e.g., Etobicoke)
   - Sedation: The type of sedation to filter by (e.g., Oral Moderate Sedation)
   - Limit: The maximum number of dentists to scrape

3. Click the "Start Scraping" button to begin the process.

4. The status area will display progress updates and any errors encountered during the scraping process.

5. Once the scraping is complete, the results will be saved to an Excel file named `dentists_in_[CITY]_filtered.xlsx` in the same directory as the script.

### Notes

- The script uses Chrome WebDriver for browser automation. Make sure you have Google Chrome installed on your system.
- The scraper uses two threads to improve performance: one starts from the first page, and the other starts from the last page and works backwards.
- The progress bar provides an estimate of the scraping progress and may not be 100% accurate due to the concurrent nature of the scraping process.
- If you encounter any issues with ChromeDriver, the script will attempt to download and use the appropriate version automatically.

### License
This project is open-source and available under the MIT License.
