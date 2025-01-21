from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from typing import List, Dict
import time

class InstamartSearchScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.setup_driver()
        self.wait = WebDriverWait(self.driver, 10)

    def setup_driver(self):
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920x1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
        except Exception as e:
            print(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def wait_for_element(self, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 10) -> bool:
        try:
            self.wait.until(EC.presence_of_element_located((by, selector)))
            return True
        except Exception as e:
            print(f"Timeout waiting for element {selector}: {str(e)}")
            return False

    def search_products(self, query: str, location: str) -> List[Dict]:
        try:
            self.driver.get('https://www.swiggy.com')
            location_input = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[id='location']")))
            location_input.send_keys(location)
            location_input.send_keys(Keys.ENTER)
            time.sleep(1)  # Wait for location to be set and page to reload

            # Select the first suggested location
            first_location = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[class*='BgUI']:nth-of-type(2) span[class*='OORn']")))
            first_location.click()
            time.sleep(1)  # Wait for the location to be confirmed

            self.driver.get('https://www.swiggy.com/instamart')
            time.sleep(1)
            encoded_query = query.replace(' ', '+')
            url = f'https://www.swiggy.com/instamart/search?custom_back=true&query={encoded_query}'
            
            print(f"Searching for: {query}")
            self.driver.get(url)

            # Wait for products to load using the exact class name
            self.wait_for_element("div.XjYJe")
            
            # Allow time for dynamic content
            time.sleep(3)
            
            return self._extract_products(self.driver.page_source)

        except Exception as e:
            print(f"Error during search: {str(e)}")
            return []

    def _extract_products(self, page_source: str) -> List[Dict]:
        products = []
        try:
            soup = BeautifulSoup(page_source, 'html.parser')
            # Using the exact class structure from the provided HTML
            product_containers = soup.find_all('div', class_="XjYJe")
            
            for container in product_containers:
                product = self._parse_product(container)
                if product:
                    products.append(product)
                
                if len(products) >= 3:  # Limit to top 3 results
                    break

        except Exception as e:
            print(f"Error extracting products: {str(e)}")
        
        return products

    def _parse_product(self, container) -> Dict:
        try:
            # Extract product details using exact classes from the HTML
            # Discount
            discount_element = container.find('div', class_="sc-aXZVg csCGOB")
            discount = discount_element.get_text() if discount_element else "No discount"

            # Name
            name_element = container.find('div', class_="novMV")
            name = name_element.get_text() if name_element else "Name not available"

            # Description
            desc_element = container.find('div', class_="sc-aXZVg hwhxsS")
            description = desc_element.get_text() if desc_element else ""

            # Delivery time
            delivery_element = container.find('div', class_="sc-aXZVg giKYGQ GOJ8s")
            delivery_time = delivery_element.get_text() if delivery_element else "No delivery info"

            # Weight/Size
            weight_element = container.find('div', class_="sc-aXZVg entQHA")
            weight = weight_element.get_text() if weight_element else "No size info"

            # Price
            mrp_element = container.find('div', class_="sc-aXZVg ihMJwf JZGfZ")
            offer_price_element = container.find('div', class_="sc-aXZVg hQJHwx")
            
            mrp = mrp_element.get_text() if mrp_element else "No MRP"
            offer_price = offer_price_element.get_text() if offer_price_element else "No offer price"

            # Image
            img_element = container.find('img', class_="sc-dcJsrY ibghhT")
            image_url = img_element.get('src') if img_element else None

            return {
                'name': name,
                # 'description': description,
                'price': mrp,
                # 'offer_price': offer_price,
                # 'discount': discount,
                'weight': weight,
                'availability': delivery_time,
                # 'image_url': image_url,
            }

        except Exception as e:
            print(f"Error parsing product: {str(e)}")
            return None

    def close(self):
        try:
            self.driver.quit()
        except Exception as e:
            print(f"Error closing driver: {str(e)}")

def main():
    scraper = InstamartSearchScraper()
    try:
        location = input("Enter your location: ")
        query = input("Enter search term: ")
        products = scraper.search_products(query, location)
        
        # Display results
        for idx, product in enumerate(products, 1):
            print(f"\nProduct {idx}:")
            print(f"Name: {product['name']}")
            print(f"Description: {product['description']}")
            print(f"MRP: {product['mrp']}")
            print(f"Offer Price: {product['offer_price']}")
            print(f"Discount: {product['discount']}")
            print(f"Weight: {product['weight']}")
            print(f"Delivery Time: {product['delivery_time']}")
           
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()