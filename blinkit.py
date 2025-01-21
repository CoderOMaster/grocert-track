import os
import json
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import base64
from openai import OpenAI
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

class BlinkitScraper:
    """
    A scraper class to extract product information from Blinkit.
    Uses OpenAI Vision to extract text from screenshots and parses product information.
    """

    def __init__(self, headless: bool = True, max_products: int = 3):
        """
        Initialize the scraper with desired settings.
        :param headless: Run browser in headless mode.
        :param max_products: Number of top products to scrape.
        """
        load_dotenv()
        self.base_url = "https://blinkit.com"
        self.max_products = max_products
        self.setup_driver(headless=headless)
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def setup_driver(self, headless: bool):
        options = Options()
        if headless:
            options.add_argument('--headless')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')

        options.add_argument('--ignore-ssl-errors=yes')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-insecure-localhost')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 15)
        self.driver.get(self.base_url)

    def set_location_to_bengaluru(self, location: str):
        """
        Set delivery location.
        :param location: Delivery location string
        """
        try:
            # Wait for the location input field to be clickable
            location_input = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//input[@name='select-locality']"))
            )
            
            time.sleep(1)
            # Simulate typing the location string character by character
            location_input.send_keys(location)
            location_input.send_keys(Keys.SPACE)
            time.sleep(1)
            location_input.send_keys(Keys.BACK_SPACE)
            time.sleep(3)
            # Wait for and select first suggestion with explicit wait
            first_suggestion = self.driver.find_element(By.CSS_SELECTOR, "div[class*='LocationSearchList']:nth-of-type(1)")
            first_suggestion.click()

            # Wait for page to update with new location
            time.sleep(5)

        except Exception as e:
            print(f"Error setting location: {str(e)}")
            raise

    def search_products(self, query: str) -> List[Dict]:
        """
        Search for products, take a screenshot, use OpenAI Vision to extract info, and return products.
        :param query: Search query string
        :return: List of product dictionaries
        """
        try:
            if not query:
                return []

            search_url = f"{self.base_url}/s/?q={query}"
            self.driver.get(search_url)
            time.sleep(5)

            # Take screenshot
            screenshot_path = "blinkit_search_screenshot.png"
            self.driver.save_screenshot(screenshot_path)

            # Extract and return products
            products = self.extract_products_from_image(screenshot_path)
            
            # Clean up screenshot
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)
                
            return products[:self.max_products]

        except Exception as e:
            print(f"Error searching products: {str(e)}")
            return []

    def extract_products_from_image(self, image_path: str) -> List[Dict]:
        """
        Extract product information from image using OpenAI Vision API.
        :param image_path: Path to screenshot image
        :return: List of product dictionaries
        """
        try:
            # Read and encode image
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user", 
                        "content": [
                            {
                                "type": "text",
                                "text": """Extract product information from this Blinkit search results image. For each product, provide these details in the following format:
                                {
                                    "name": "product name",
                                    "price": "price in rupees symbol rather than its character string which is \u20b9",
                                    "weight": "weight/quantity if shown",
                                    "availability": "in stock or out of stock",
                                }
                                Return the data for top 3 products in json format and nothing else not even comments or anything else"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )

            # Parse response and handle potential JSON formatting issues
            content = response.choices[0].message.content.strip()
            # Extract JSON array if embedded in other text
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = content[start_idx:end_idx]
                products = json.loads(json_str)
                print("Extracted Products:")
                print(json.dumps(products, indent=2))
                return products
            else:
                print("No valid JSON array found in response")
                return []

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {str(e)}")
            print("Raw response:", response.choices[0].message.content)
            return []
        except Exception as e:
            print(f"Error extracting products: {str(e)}")
            return []

    def close(self):
        """
        Close the WebDriver.
        """
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()

def main():
    """
    Main function to execute the scraper.
    """
    HEADLESS = True
    MAX_PRODUCTS = 3

    scraper = BlinkitScraper(headless=HEADLESS, max_products=MAX_PRODUCTS)
    try:
        query = input("Enter search term: ").strip()
        location = input("Enter delivery location: ").strip()
        
        scraper.set_location_to_bengaluru(location)
        products = scraper.search_products(query)

        if not products:
            print("No products found.")

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
