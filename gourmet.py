from typing import List, Dict
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import urllib.parse
import time

class GourmetGardenScraper:
    """
    A scraper class to extract product information from GourmetGarden.
    """

    def __init__(self, headless: bool = True, max_products: int = 3):
        """
        Initialize the scraper with desired settings.

        :param headless: Run browser in headless mode.
        :param max_products: Number of top products to scrape.
        :param save_format: Format to save data ('csv' or 'json').
        """
        self.max_products = max_products
        # self.save_format = save_format.lower()
        self.setup_driver(headless=headless)
        self.wait = WebDriverWait(self.driver, 15)

    def setup_driver(self, headless: bool):
        """
        Configure and initialize the Chrome WebDriver.

        :param headless: Run browser in headless mode.
        """
        options = Options()
        if headless:
          options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        print("WebDriver initialized successfully.")

    def search_products(self, query: str) -> List[Dict]:
        """
        Search for products and extract their information.

        :param query: Search term
        :return: List of product dictionaries
        """
        try:
            # URL encode the search query to handle spaces and special characters
            encoded_query = urllib.parse.quote(query)
            
            # Navigate directly to search URL
            search_url = f"https://gourmetgarden.in/search?q={encoded_query}"
            self.driver.get(search_url)
            print(f"Navigating to search URL: {search_url}")

            # Handle location popup
            try:
                location_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.popup-btn[onclick*='setCookie']")))
                location_btn.click()
                print("Location popup handled successfully")
            except Exception as e:
                print(f"Could not handle location popup: {str(e)}")


            # Wait for product cards to load
            self.driver.get(search_url)
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "card__info")))

            
            products = []
            product_cards = self.driver.find_elements(By.CLASS_NAME, "card__info")[:self.max_products]

            for card in product_cards:
                try:
                    # Get product title and link
                    time.sleep(3)
                    title_element = card.find_element(By.CSS_SELECTOR, ".card__title")
                    product_name = title_element.text.strip()
                    product_link = title_element.get_attribute('href')

                    # Get product description
                    description = card.find_element(By.CSS_SELECTOR, ".card__description").text.strip()

                    # Get price information
                    current_price = card.find_element(By.CSS_SELECTOR, ".product__price--sale").text.replace('₹', '').strip()
                    original_price = card.find_element(By.CSS_SELECTOR, ".add-to-cart__success--sale").text.replace('₹', '').strip()

                    # Get variant/size information
                    try:
                        variant = card.find_element(By.CSS_SELECTOR, ".swatch--active").text
                    except:
                        variant = "N/A"

                    # Get stock status based on add to cart button
                    try:
                        add_to_cart = card.find_element(By.CSS_SELECTOR, ".button--addToCart")
                        stock_status = "In Stock" if add_to_cart.is_enabled() else "Out of Stock"
                    except:
                        stock_status = "N/A"

                    product = {
                        'Name': product_name,
                        # 'Link': product_link,
                        'Description': description,
                        'Price': current_price,
                        'Variant': variant,
                        'Stock': stock_status
                    }

                    products.append(product)

                except Exception as e:
                    print(f"Error extracting product details: {str(e)}")
                    continue

            return [
                {
                    "name": product.get("Name", "N/A"),
                    "weight": product.get("Variant", "N/A"),
                    "price": product.get("Price", "N/A"),
                    "availability": product.get("Stock", "N/A")
                }
                for product in products
            ]

        except Exception as e:
            print(f"Error extracting products: {str(e)}")
            return []


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
    HEADLESS = True  # Set to False if you want to see the browser
    MAX_PRODUCTS = 3  # Number of top products to scrape

    scraper = GourmetGardenScraper(headless=HEADLESS, max_products=MAX_PRODUCTS)
    try:
        query = input("Enter search term: ").strip()
        if not query:
            print("No search term entered. Exiting.")
            print("No search term entered by the user.")
            return

        products = scraper.search_products(query)

        if not products:
            print("No products found.")
            print("No products found for the given query.")
        else:
            # Display results
            for idx, product in enumerate(products, 1):
                print(f"\nProduct {idx}:")
                print(f"Name: {product['name']}")
                print(f"Weight: {product['weight']}")
                print(f"Price: ₹{product['price']}")
                print(f"Availability: {product['availability']}")
                # print(f"Link: {product['Link']}")
              
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
