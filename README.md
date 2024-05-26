# RCDSO Scraper
This Python script scrapes dentist information from the Royal College of Dental Surgeons of Ontario (RCDSO) website. It uses Selenium with Chrome WebDriver to automate the browsing and extraction of data.
## Features

- Scrapes dentist information including name, business name, and address
- Handles pagination to scrape multiple pages of results
- Saves the scraped data to an Excel file
- Configurable search URL and limit for the number of dentists to scrape

## Requirements

- Python 3.x
- Selenium
- pandas
- webdriver_manager

## Installation

1. Clone the repository:

```git clone https://github.com/yourusername/dentist-scraper.git```

2. Install the required dependencies:

```pip install -r requirements.txt```


## Usage

1. Open the ```scraper.py``` file and modify the following variables according to your requirements:

- ```base_url```: The base URL for the RCDSO dentist search page
- ```test_limit```: The maximum number of dentists to scrape


2. Run the script:
```python scraper.py```

3. The script will start scraping dentist information from the specified URL. It will display the progress and any errors encountered during the process.
4. Once the scraping is complete, the results will be saved to an Excel file named dentists_in_FILENAME.xlsx in the same directory.

### Notes

- The script is set to scrape dentists from the city of Brampton. Modify the city name in the code if you want to scrape dentists from a different city.
- The script uses Chrome WebDriver for browser automation. Make sure you have Chrome browser installed on your system.
- The script handles pagination by scrolling to the bottom of the page and clicking the "Next" button if available. It will continue scraping until the specified limit is reached or there are no more results to load.

### License
This project is open-source and available under the MIT License.
