import os
import sys
from typing import List, Dict, Optional
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd


class HealthyBuddhaScraper:
    """
    A scraper class to extract product information from HealthyBuddha.
    """

    def __init__(self, headless: bool = True, max_products: int = 3, save_format: str = 'csv'):
        """
        Initialize the scraper with desired settings.

        :param headless: Run browser in headless mode.
        :param max_products: Number of top products to scrape.
        :param save_format: Format to save data ('csv' or 'json').
        """
        self.max_products = max_products
        self.save_format = save_format.lower()
        self.setup_driver(headless=headless)
        self.wait = WebDriverWait(self.driver, 15)
        self.base_url = "https://healthybuddha.in"

    def setup_driver(self, headless: bool):
        """
        Configure and initialize the Chrome WebDriver.

        :param headless: Run browser in headless mode.
        """
        options = Options()
        if headless:
            options.add_argument('--headless=new')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')

        user_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/120.0.0.0 Safari/537.36")
        options.add_argument(f'--user-agent={user_agent}')

        # use_profile = False
        # if use_profile:
        #     chrome_profile = self.get_chrome_profile_path()
        #     if chrome_profile:
        #         options.add_argument(f'--user-data-dir={chrome_profile}')
        #         options.add_argument('--profile-directory=Default')
        #         print(f"Using Chrome profile at: {chrome_profile}")
        #     else:
        #         print("Chrome profile path not found. Proceeding without it.")

        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            print("WebDriver successfully initialized.")
        except Exception as e:
            print(f"Failed to initialize WebDriver: {str(e)}")
            raise

    # @staticmethod
    # def get_chrome_profile_path() -> Optional[str]:
    #     """
    #     Get the path to the Chrome user profile based on the operating system.

    #     :return: Path to Chrome user data directory or None if not found.
    #     """
    #     username = os.getenv('USERNAME') or os.getenv('USER')
    #     if not username:
    #         return None

    #     if sys.platform.startswith('win'):
    #         path = f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data"
    #     elif sys.platform.startswith('darwin'):
    #         path = f"/Users/{username}/Library/Application Support/Google/Chrome"
    #     else:  # Assume Unix/Linux
    #         path = f"/home/{username}/.config/google-chrome"

    #     if os.path.exists(path):
    #         return path
    #     return None

    def search_products(self, query: str) -> List[Dict]:
        """
        Search for products on HealthyBuddha and extract product details.

        :param query: Search term.
        :return: List of dictionaries containing product information.
        """
        if not query:
            print("Empty search query provided.")
            return []

        try:
            encoded_query = query.replace(' ', '+')
            search_url = f"{self.base_url}/index.php?search={encoded_query}&sub_category=1&route=product%2Fsearch"
            
            self.driver.get(search_url)
            print(f"Navigated to search URL: {search_url}")

            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".product-block")
            ))
            print("Search results loaded.")

            products = self.extract_products()
            print(f"Extracted {len(products)} products.")

            return products

        except Exception as e:
            print(f"Error during search: {str(e)}")
            return []

    def extract_products(self) -> List[Dict]:
        """
        Extract product details from the search results.

        :return: List of dictionaries containing product information.
        """
        products = []
        try:
            product_cards = self.driver.find_elements(By.CSS_SELECTOR, ".product-block")[:self.max_products]
            print(f"Found {len(product_cards)} product cards.")

            for card in product_cards:
                try:
                    # Extract basic product info
                    product = {
                        'Name': card.find_element(By.CSS_SELECTOR, ".name a").text.strip(),
                        'Link': card.find_element(By.CSS_SELECTOR, ".name a").get_attribute('href'),
                        'Image': card.find_element(By.CSS_SELECTOR, ".product-img").get_attribute('src'),
                        'Description': card.find_element(By.CSS_SELECTOR, ".description").text.strip(),
                        'Price': card.find_element(By.CSS_SELECTOR, ".special-price").text.replace('Rs', '').strip()
                    }

                    # Extract quantity/weight info
                    try:
                        product['Weight'] = card.find_element(By.CSS_SELECTOR, ".price-qty").text.strip()
                    except:
                        product['Weight'] = "N/A"

                    # Check if product is new
                    try:
                        new_label = card.find_element(By.CSS_SELECTOR, ".labl_ofr").text.strip()
                        product['Is_New'] = new_label == "New"
                    except:
                        product['Is_New'] = False

                    # Get stock status
                    try:
                        add_to_cart = card.find_element(By.CSS_SELECTOR, ".button-cart")
                        product['Stock'] = "In Stock" if add_to_cart.is_enabled() else "Out of Stock"
                    except:
                        product['Stock'] = "N/A"

                    products.append(product)

                except Exception as e:
                    print(f"Error extracting product details: {str(e)}")
                    continue

            return [
                {
                    "name": product.get("Name", "N/A"),
                    "weight": product.get("Weight", "N/A"),
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
    # SAVE_FORMAT = 'csv'  # 'csv' or 'json'

    scraper = HealthyBuddhaScraper(headless=HEADLESS, max_products=MAX_PRODUCTS)
    try:
        query = input("Enter search term: ").strip()
        if not query:
            print("No search term entered. Exiting.")
            print("No search term entered by the user.")
            return

        products = scraper.search_products(query)

        if not products:
            print("No products found.")
        else:
            # Display results
            for idx, product in enumerate(products, 1):
                print(f"\nProduct {idx}:")
                print(f"Name: {product['Name']}")
                print(f"Price: Rs {product['Price']}")
                print(f"Weight: {product['Weight']}")
                print(f"Stock: {product['Stock']}")
                # print(f"New Product: {'Yes' if product['Is_New'] else 'No'}")
                # print(f"Link: {product['Link']}")
                # print(f"Description: {product['Description'][:200]}...")

            # Save results
            # scraper.save_data(products)

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
