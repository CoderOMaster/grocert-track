import json
from datetime import datetime
from healthybuda import HealthyBuddhaScraper
from instamart import InstamartSearchScraper
from nature import NaturesBasketScraper
from zepto import ZeptoSearchScraper
from bigbasket import BigBasketScraper
from gourmet import GourmetGardenScraper
from blinkit import BlinkitScraper
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def find_relevant_matches(products: list, query: str) -> dict:
    """
    Use LLM to find relevant product matches based on search query.
    
    Args:
        products (list): List of product dictionaries to analyze
        query (str): Original search query to match against
        
    Returns:
        dict: Filtered list of relevant product matches
    """
    prompt = f"""Given the search query "{query}", analyze these product listings and return only the most relevant matches:
    {json.dumps(products, indent=2)}
    
    Return the filtered results in the same JSON format, keeping only products that closely match the search query.
    Consider product names, descriptions, price(keep rupees symbol intact) and other attributes to determine relevance."""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    try:
        return json.loads(response.choices[0].message.content)
    except:
        print("Error parsing LLM response, returning all results")
        return {"matches": products}

def scrape_and_collect(query: str, location: str = None, pincode: str = None) -> dict:
    """
    Scrape product data from multiple sources and use LLM to find relevant matches.
    
    Args:
        query (str): Search query
        location (str, optional): Location for delivery. Required for some platforms.
        pincode (str, optional): Pincode for specific location-based searches.
    
    Returns:
        dict: Combined results from all scrapers filtered for relevance
    """
    all_products = []

    # Scrapers that require location
    if location:
        try:
            zepto_scraper = ZeptoSearchScraper(headless=True)
            zepto_products = zepto_scraper.search_products(query, location)
            for product in zepto_products:
                product['platform'] = 'Zepto'
                all_products.append(product)
            zepto_scraper.close()
        except Exception as e:
            print(f"Error with Zepto scraper: {str(e)}")

        try:
            instamart_scraper = InstamartSearchScraper(headless=True)
            instamart_products = instamart_scraper.search_products(query, location)
            for product in instamart_products:
                product['platform'] = 'Instamart'
                all_products.append(product)
            instamart_scraper.close()
        except Exception as e:
            print(f"Error with Instamart scraper: {str(e)}")

        try:
            blinkit_scraper = BlinkitScraper(headless=True, max_products=3)
            blinkit_scraper.set_location_to_bengaluru(location)
            blinkit_products = blinkit_scraper.search_products(query)
            for product in blinkit_products:
                product_with_platform = dict(product)
                product_with_platform['platform'] = 'Blinkit'
                all_products.append(product_with_platform)
            blinkit_scraper.close()
        except Exception as e:
            print(f"Error with Blinkit scraper: {str(e)}")

    # Scrapers that don't require location
    try:
        healthy_scraper = HealthyBuddhaScraper(headless=True)
        healthy_products = healthy_scraper.search_products(query)
        for product in healthy_products:
            product['platform'] = 'HealthyBuddha'
            all_products.append(product)
        healthy_scraper.close()
    except Exception as e:
        print(f"Error with HealthyBuddha scraper: {str(e)}")

    try:
        gourmet_scraper = GourmetGardenScraper(headless=True)
        gourmet_products = gourmet_scraper.search_products(query)
        for product in gourmet_products:
            product['platform'] = 'GourmetGarden'
            all_products.append(product)
        gourmet_scraper.close()
    except Exception as e:
        print(f"Error with GourmetGarden scraper: {str(e)}")

    try:
        bigbasket_scraper = BigBasketScraper(headless=True)
        bigbasket_products = bigbasket_scraper.search_products(query)
        for product in bigbasket_products:
            product['platform'] = 'BigBasket'
            all_products.append(product)
        bigbasket_scraper.close()
    except Exception as e:
        print(f"Error with BigBasket scraper: {str(e)}")

    try:
        natures_scraper = NaturesBasketScraper(headless=True)
        if pincode:
            natures_scraper.set_pincode(pincode)
        natures_products = natures_scraper.search_products(query)
        for product in natures_products:
            product['platform'] = "Nature's Basket"
            all_products.append(product)
        natures_scraper.close()
    except Exception as e:
        print(f"Error with Nature's Basket scraper: {str(e)}")
    print(all_products)
    return {"matches": all_products}

def main():
    query = input("Enter search query: ")
    location = input("Enter delivery location (press Enter to skip): ") or None
    pincode = input("Enter pincode (press Enter to skip): ") or None
    output_file = input("Enter output file name (press Enter for default 'results.json'): ") or 'results.json'

    # Run scraper
    results = scrape_and_collect(query, location, pincode)
    final_results = find_relevant_matches(results["matches"], query)
    
    # Save results to file
    with open(output_file, 'w') as f:
        json.dump(final_results, f, indent=2)
        
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()
