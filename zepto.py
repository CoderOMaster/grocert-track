from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from typing import List, Dict
import time
import pandas as pd
from datetime import datetime
import os

class ZeptoSearchScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.setup_driver()
        self.wait = WebDriverWait(self.driver, 10)
        self.base_url = "https://www.zeptonow.com"

    def setup_driver(self):
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--window-size=1920x1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
    
        # Add these lines to use your Chrome profile
        # chrome_profile = f"C:\\Users\\{os.getenv('USERNAME')}\\AppData\\Local\\Google\\Chrome\\User Data"
        # options.add_argument(f'--user-data-dir={chrome_profile}')
        # options.add_argument('--profile-directory=Default')  # or your specific profile name
    
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/120.0.0.0 Safari/537.36')

        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            print("WebDriver successfully initialized.")
        except Exception as e:
            print(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def wait_for_element(self, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 10) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, selector)))
            return True
        except Exception as e:
            print(f"Timeout waiting for element {selector}: {str(e)}")
            return False

    def search_products(self, query: str, location: str) -> List[Dict]:
        try:
            self.driver.get(self.base_url)
            print(f"Navigated to {self.base_url}")

            # Wait for and click the 'Select Location' button
            location_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Select Location')]")))
            location_button.click()
            print("Clicked on 'Select Location' button.")

            # Wait for location input and enter the location
            location_input = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//input[contains(@class, 'focus')]")))
            location_input.send_keys(location)
            print(f"Entered location: {location}")

            # Select the first option from the dropdown
            first_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@data-testid='address-search-item'][1]//h4[contains(@class, 'font-heading')]")))
            first_option.click()
            print("Selected the first location suggestion.")

            # Click on the 'Confirm Action' button
            confirm_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Confirm Action']/div[@class='flex items-center justify-center']")))
            confirm_button.click()
            print("Clicked on 'Confirm Action' button.")

            encoded_query = query.replace(' ', '+')
            search_url = f"{self.base_url}/search?query={encoded_query}"

            print(f"Searching for: {query}")
            self.driver.get(search_url)

            # Wait for products to load
            if not self.wait_for_element("a[data-testid='product-card']"):
                print("No products found for the query.")
                return []

            # Scroll to load more products
            self.scroll_page()

            return self._extract_products(self.driver.page_source)

        except Exception as e:
            print(f"Error during search: {str(e)}")
            return []

    def scroll_page(self):
        """Scroll page to load more products"""
        try:
            print("Starting to scroll the page to load all products.")
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for new content to load
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    print("Reached the bottom of the page.")
                    break
                last_height = new_height
        except Exception as e:
            print(f"Error scrolling page: {str(e)}")

    def _extract_products(self, page_source: str) -> List[Dict]:
        products = []
        try:
            soup = BeautifulSoup(page_source, 'html.parser')
            # Find all product cards using the data-testid attribute
            product_cards = soup.find_all('a', attrs={'data-testid': 'product-card'})

            print(f"Found {len(product_cards)} product cards.")

            for card in product_cards:
                product = self._parse_product(card)
                if product:
                    products.append(product)

                if len(products) >= 3:  # Limit to top 3 results
                    print("Collected top 3 products.")
                    break

        except Exception as e:
            print(f"Error extracting products: {str(e)}")

        print(f"Extracted {len(products)} products.")
        return [
            {
                "name": product.get("name", "N/A"),
                "weight": product.get("weight", "N/A"),
                "price": product.get("price", "N/A"),
                "availability": product.get("availability", "N/A")
            }
            for product in products
        ]

    def _parse_product(self, card) -> Dict:
        try:
            # Extract product details using data-testid attributes
            name_element = card.find('h5', attrs={'data-testid': 'product-card-name'})
            name = name_element.get_text().strip() if name_element else "Name not available"

            # Extract quantity/weight
            quantity_element = card.find('span', attrs={'data-testid': 'product-card-quantity'})
            weight = quantity_element.find('h4').get_text().strip() if quantity_element and quantity_element.find('h4') else "No size info"

            # Extract price
            price_element = card.find('h4', attrs={'data-testid': 'product-card-price'})
            price = price_element.get_text().strip() if price_element else "Price not available"

            # Extract MRP (original price)
            mrp_element = card.find('p', {'class': 'font-body text-xs line-clamp-1 !m-0 ml-1 !text-3xs text-skin-primary-void/40 line-through sm:!text-2xs'})
            mrp = mrp_element.get_text().strip() if mrp_element else price

            # Extract discount
            discount_element = card.find('p', {'class': 'absolute top-0 text-center font-title text-white px-[4px] pt-[1.75px] text-[0.6rem]'})
            discount = discount_element.get_text().strip() if discount_element else "No discount"

            # Extract image URL
            img_element = card.find('img', attrs={'data-testid': 'product-card-image'})
            image_url = img_element.get('src') if img_element else None

            # Extract add to cart button status
            add_button = card.find('button', attrs={'data-testid': 'product-card-add-btn'})
            availability = "Available" if add_button else "Not Available"

            return {
                'name': name,
                'weight': weight,
                'price': price,
                'mrp': mrp,
                'discount': discount,
                'image_url': image_url,
                'availability': availability,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            print(f"Error parsing product: {str(e)}")
            return None


    def close(self):
        try:
            self.driver.quit()
            print("WebDriver closed successfully.")
        except Exception as e:
            print(f"Error closing driver: {str(e)}")


def main():
    scraper = ZeptoSearchScraper(headless=True)  # Set headless=False if you want to see the browser
    try:
        # Get location and search query
        location = input("Enter your location: ").strip()
        if not location:
            print("No location entered. Exiting.")
            return

        query = input("Enter search term: ").strip()
        if not query:
            print("No search term entered. Exiting.")
            return

        products = scraper.search_products(query, location)

        if not products:
            print("No products found.")
        else:
            # Display results
            for idx, product in enumerate(products, 1):
                print(f"\nProduct {idx}:")
                print(f"Name: {product['name']}")
                print(f"Weight: {product['weight']}")
                print(f"Price: {product['price']}")
                print(f"MRP: {product['mrp']}")
                print(f"Discount: {product['discount']}")
                print(f"Availability: {product['availability']}")
                print(f"Image URL: {product['image_url']}")

            # Save results
            # timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # filename = f'zepto_results_{timestamp}.csv'
            # scraper.save_to_csv(products, filename=filename)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
