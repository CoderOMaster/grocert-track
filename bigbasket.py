import os
import sys
from typing import List, Dict, Optional
from datetime import datetime
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from webdriver_manager.chrome import ChromeDriverManager


class BigBasketScraper:
    """
    A scraper class to extract product information from BigBasket.
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
        self.base_url = "https://www.bigbasket.com"
        self.setup_driver(headless=headless)
        self.wait = WebDriverWait(self.driver, 15)

    def setup_driver(self, headless: bool = True):
        """
        Initialize the Selenium WebDriver with desired options.

        :param headless: Run browser in headless mode.
        """
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--window-size=1920x1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--disable-dev-shm-usage')

        user_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36")
        options.add_argument(f'--user-agent={user_agent}')

        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            print("WebDriver successfully initialized.")
            
            # Set location cookies for Bengaluru
            self.driver.get(self.base_url)
            location_cookies = [
                {
                    'name': 'bb_location_info',
                    'value': '{"addressId":7,"regionId":1,"area":"Bengaluru","areaId":1,"cityId":1,"city":"Bengaluru"}',
                    'domain': '.bigbasket.com'
                },
                {
                    'name': 'bb_home_location',
                    'value': '{"regionId":1,"areaId":1,"areaName":"Bengaluru","cityId":1,"cityName":"Bengaluru"}',
                    'domain': '.bigbasket.com'
                }
            ]
            
            for cookie in location_cookies:
                self.driver.add_cookie(cookie)
                
            print("Location cookies set for Bengaluru")
            
        except Exception as e:
            print(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def search_products(self, query: str) -> List[Dict]:
        """
        Search for products on BigBasket and extract product details.

        :param query: Search term.
        :return: List of dictionaries containing product information.
        """
        if not query:
            print("Empty search query provided.")
            return []

        try:
            # Directly go to search URL with location cookies set
            encoded_query = query.replace(' ', '+')
            search_url = f"{self.base_url}/ps/?q={encoded_query}&nc=as"
            
            self.driver.get(search_url)
            print(f"Navigated to search URL: {search_url}")

            # Wait for search results to load
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.SKUDeck___StyledDiv-sc-1e5d9gk-0")
            ))
            print("Search results loaded.")

            # Extract product details
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
            # Scroll to load dynamic content if necessary
            self.scroll_to_bottom()

            # Locate product cards
            product_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.SKUDeck___StyledDiv-sc-1e5d9gk-0")[:self.max_products]
            print(f"Found {len(product_cards)} product cards.")

            for idx, card in enumerate(product_cards, 1):
                try:
                    # Extract product details using updated selectors
                    name = card.find_element(By.CSS_SELECTOR, "h3.block.m-0.line-clamp-2").text.strip()
                    brand = card.find_element(By.CSS_SELECTOR, "span.Label-sc-15v1nk5-0.BrandName___StyledLabel2-sc-hssfrl-1").text.strip()
                    price = card.find_element(By.CSS_SELECTOR, "span.Label-sc-15v1nk5-0.Pricing___StyledLabel-sc-pldi2d-1").text.strip()
                    
                    try:
                        rating = card.find_element(By.CSS_SELECTOR, "span.Label-sc-15v1nk5-0.gJxZPQ").text.strip()
                        reviews = card.find_element(By.CSS_SELECTOR, "span.Label-sc-15v1nk5-0.ReviewsAndRatings___StyledLabel-sc-2rprpc-1").text.strip()
                    except:
                        rating = "N/A"
                        reviews = "0 Ratings"

                    try:
                        weight = card.find_element(By.CSS_SELECTOR, "span.Label-sc-15v1nk5-0.PackChanger___StyledLabel-sc-newjpv-1").text.strip()
                    except:
                        weight = "N/A"

                    try:
                        offer_price = card.find_element(By.CSS_SELECTOR, "span.Label-sc-15v1nk5-0.gJxZPQ.lg\\:text-sm.xl\\:text-md").text.strip()
                    except:
                        offer_price = price

                    products.append({
                        'Name': name,
                        'Brand': brand,
                        'Price': price,
                        'Offer_Price': offer_price,
                        'Weight': weight,
                        'Rating': rating,
                        'Reviews': reviews
                    })
                    print(f"Extracted product {idx}: {name}")

                except Exception as e:
                    print(f"Error extracting details for product {idx}: {str(e)}")
                    continue

        except Exception as e:
            print(f"Error extracting products: {str(e)}")

        return [
            {
                "name": product.get("Name", "N/A"),
                "weight": product.get("Weight", "N/A"),
                "price": product.get("Price", "N/A"),
                "availability": product.get("Rating", "N/A")  # Assuming availability is represented by rating
            }
            for product in products
        ]

    def scroll_to_bottom(self):
        """
        Scroll to the bottom of the page to ensure all products are loaded.
        """
        try:
            print("Scrolling to the bottom of the page to load all products.")
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.driver.implicitly_wait(2)  # Wait for content to load
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    print("Reached the bottom of the page.")
                    break
                last_height = new_height
        except Exception as e:
            print(f"Error during scrolling: {str(e)}")


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
    SAVE_FORMAT = 'csv'  # 'csv' or 'json'

    scraper = BigBasketScraper(headless=HEADLESS, max_products=MAX_PRODUCTS, save_format=SAVE_FORMAT)
    try:
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
                print(f"Weight: {product['weight']}")
                print(f"Price: {product['price']}")
                print(f"Availability: {product['availability']}")

            # Save results
            scraper.save_data(products)

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
