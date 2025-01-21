import os
import json
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time


class NaturesBasketScraper:
    """
    A scraper class to extract product information from Nature's Basket.
    """

    def __init__(self, headless: bool = True, max_products: int = 3, save_format: str = 'csv'):
        """
        Initialize the scraper with desired settings.

        :param headless: Run browser in headless mode.
        :param max_products: Number of top products to scrape.
        :param save_format: Format to save data ('csv' or 'json').
        """
        self.base_url = "https://www.naturesbasket.co.in"
        self.max_products = max_products
        self.save_format = save_format.lower()
        # self.cookies_file = "naturesbasket_cookies.json"
        self.pincode = None  # Initialize pincode as None

        
        self.setup_driver(headless=headless)
        self.wait = WebDriverWait(self.driver, 15)

    def setup_driver(self, headless: bool):
        """
        Configure and initialize the Chrome WebDriver.

        :param headless: Run browser in headless mode.
        """
        # try:
        options = Options()
        if headless:
                options.add_argument('--headless=new')
                options.add_argument('--disable-gpu')
            
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--allow-insecure-localhost')
        options.add_argument('--window-size=1920,1080')
            
            # Add custom user agent

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 15)

            # First navigate to base domain
        self.driver.get(self.base_url)
        if self.pincode:
            self.set_pincode(self.pincode)
        print("Initial navigation to base domain")


    def set_pincode(self, pincode: str):
        """
        Set the delivery pincode automatically.
        """
        try:
            # Wait for the pincode input to appear
            pincode_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "txt"))
            )
            pincode_input.clear()
            pincode_input.send_keys(pincode)

            # Click the OK button after entering the pincode
            submit_button = self.wait.until(
                 EC.element_to_be_clickable((By.XPATH, "//input[@id='btnAddPin' and @value='SUBMIT' and @type='button']")))
            submit_button.click()


            ok_button = self.wait.until(
                 EC.element_to_be_clickable((By.XPATH, "//input[@id='btnAddPin' and @value='OK' and @type='button']")))
            
            ok_button.click()

            print(f"Pincode set to {pincode} successfully.")
            # Give some time for the location change to take effect
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".location-confirmed-message")))
            print("Location confirmed.")

        except Exception as e:
            print(f"Error setting pincode: {str(e)}")    

    def search_products(self, query: str) -> List[Dict]:
        """
        Search for products and extract their information.

        :param query: Search term
        :return: List of product dictionaries
        """
        try:
            # Navigate to base URL
            self.driver.get(self.base_url)
            print(f"Navigated to {self.base_url}")
            time.sleep(2)
            # Wait for the search input to be present and visible
            search_input = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//div[@id='ctl00_divPnlMasterSearch1']//input[@id='ctl00_txtMasterSearch1']"))
        )
            self.driver.execute_script("arguments[0].scrollIntoView();", search_input)
            search_input.click()
            search_input.clear()
            search_input.send_keys(query)
            print(f"Entered search query: {query}")

        # Submit search query
            search_input.send_keys(Keys.RETURN)
            print("Search submitted.")

        # Wait for the results to load
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class*="pro-id_"]')))
            print("Search results loaded.")
            # Extract product details
            products = self.extract_products()
            print(f"Extracted {len(products)} products.")

            return products

        except Exception as e:
            print(f"Error extracting products: {str(e)}")
            return []

    def extract_products(self) -> List[Dict]:
        """
        Extract product details from the search results.

        :return: List of product dictionaries
        """
        products = []
        try:
            product_cards = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="pro-id_"]')[:self.max_products]
            print(f"Found {len(product_cards)} product cards.")

            for idx, card in enumerate(product_cards, 1):
                try:
                    # Get product title and link
                    title_element = card.find_element(By.CSS_SELECTOR, ".search_Ptitle")
                    product_name = title_element.text.strip()
                    # product_link = title_element.get_attribute('href')

                    # Get product description
                    # Description not available in provided HTML

                    # Get price information
                    try:
                        price_element = card.find_element(By.CSS_SELECTOR, ".search_PSellingP")
                        price_text = price_element.text.strip()
                        # Keep price as string
                        current_price = price_text.replace('MRP ', '')
                        original_price = "N/A"  # Original price not available
                    except:
                        current_price = "N/A"
                        original_price = "N/A"

                    # Get variant/size information
                    try:
                        variant = card.find_element(By.CSS_SELECTOR, ".search_PSelectedSize").text.strip()
                    except:
                        variant = "N/A"

                    # Get stock status
                    # Stock status not available in provided HTML
                    stock_status = "N/A"

                    product = {
                        'Name': product_name,
                        # 'Link': product_link,
                        # '': description,
                        'Price': current_price,
                        'Variant': variant,
                        'Stock': stock_status
                    }

                    products.append(product)
                    print(f"Extracted product {idx}: {product_name}")

                except Exception as e:
                    print(f"Error extracting product details: {str(e)}")
                    continue

        except Exception as e:
            print(f"Error extracting products: {str(e)}")

        return [
            {
                "name": product.get("Name", "N/A"),
                "weight": product.get("Variant", "N/A"),
                "price": product.get("Price", "N/A"),
                "availability": product.get("Stock", "N/A")
            }
            for product in products
        ]

    

    def close(self):
        """
        Close the WebDriver.
        """
        try:
            if self.driver:
                self.driver.quit()
                print("WebDriver closed successfully.")
        except Exception as e:
            print(f"Error closing WebDriver: {str(e)}")


def main():
    """
    Main function to execute the scraper.
    """
    # Configuration
    HEADLESS = True# Set to False if you want to see the browser
    MAX_PRODUCTS = 3  # Number of top products to scrape
    # SAVE_FORMAT = 'csv'  # 'csv' or 'json'

    scraper = NaturesBasketScraper(headless=HEADLESS, max_products=MAX_PRODUCTS)
    try:
        pincode = input("Enter your pincode: ").strip()
        if not pincode:
            print("No pincode entered. Exiting.")
            return
        scraper.pincode = pincode
        scraper.set_pincode(pincode)

        query = input("Enter search term: ").strip()
        if not query:
            print("No search term entered. Exiting.")
            return

        products = scraper.search_products(query)

        if not products:
            print("No products found.")
        else:
            # Display results
            for idx, product in enumerate(products, 1):
                print(f"\nProduct {idx}:")
                print(f"Name: {product['name']}")
                print(f"Current Price: ₹{product['price']}")
                print(f"Variant: {product['weight']}")
                print(f"Stock Status: {product['availability']}")

            # Save results

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
