import pymongo
import uuid
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from webdriver_manager.chrome import ChromeDriverManager

class DarazScraper:
    def __init__(self, search_query, collection_name):
        self.search_query = search_query
        self.collection_name = collection_name
        self.products = []
        try:
            self.client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
            self.client.server_info() 
            self.db = self.client["daraz_db"]
            self.collection = self.db[self.collection_name]
        except pymongo.errors.ServerSelectionTimeoutError:
            print("Error: Unable to connect to MangoDB.")
            exit()
        except Exception as e:
            print(f"MongoDB Connection Error: {e}")
            exit()
        self.driver = None
        self.client = pymongo.MongoClient("mongodb://localhost:27017/")
        self.db = self.client["daraz_db"]
        self.collection = self.db[self.collection_name]
        self.driver = None

    def setup_driver(self):
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        self.driver.get('https://www.daraz.pk/')
        self.driver.maximize_window()

    def search_product(self):
        try:
            search_box = WebDriverWait(self.driver, 10).until(
                ec.visibility_of_element_located((By.ID, "q")) )
            search_box.clear()
            search_box.send_keys(self.search_query)
            search_button = WebDriverWait(self.driver, 10).until(
                ec.element_to_be_clickable((By.CLASS_NAME, "search-box__button--1oH7")) )
            search_button.click()
        except Exception as e:
            print(f"Error during search: {e}")

    def scrape_data(self):
        try:
            all_products = WebDriverWait(self.driver, 10).until(
                ec.presence_of_all_elements_located((By.XPATH, './/div[@class="Ms6aG"]')) )
            for product in all_products:
                product_data = self.extract_product_data(product)
                self.products.append(product_data)
                self.collection.insert_one(product_data)
        except Exception as e:
            print(f"Error during data scraping: {e}")

    def name(self, product):
        return self.get_text(product,'.//div[@class="RfADt"]')  

    def price_amount(self, product):
        return f"{self.get_text(product, './/span[@class=\"ooOxS\"]')}"  


    def reviews(self, product):
        try:
            review_elements = product.find_elements(By.XPATH, './/div[@class="mdmmT _32vUv"]')
            return [review.text.strip() for review in review_elements if review.text.strip()]
        except Exception as e:
            print(f"Error fetching reviews: {e}")
            return []

    def images(self, product):
        try:
            images = product.find_elements(By.XPATH, './/img[@type="product"]')
            return [{"url": img.get_attribute("src"), "alt_text": img.get_attribute("alt") or ""} for img in images]
        except Exception as e:
            print(f"Error extracting images: {e}")
            return []

    def get_text(self, parent, xpath):
        try:
            element = parent.find_element(By.XPATH, xpath)
            return element.text.strip() if element.text else "N/A" 
        except Exception as e:
            print(f"Error fetching text for xpath {xpath}: {e}")
            return "N/A"  

    def close_driver(self):
        if self.driver:
            self.driver.quit()

    def run(self):
        try:
            self.setup_driver()
            self.search_product()
            self.scrape_data()
        finally:
            self.close_driver()
        print("Data successfully stored in MongoDB.")

    def extract_product_data(self, product):
        return {
            "product_id": str(uuid.uuid4()),
            "name": self.name(product),
            "description": "",
            "category": "",
            "brand": "",
            "actual_price": {
                "amount": self.price_amount(product),
                "currency": "PKR"
            },
            "discount_percent": None,
            "discounted_price": {
                "amount": self.price_amount(product),
                "currency": ""
            },
            "availability": {
                "in_stock": True,
                "quantity": None
            },
            "seller_ratings_percent": None,
            "ship_on_time_percent": None,
            "chat_response_rate_percent": None,
            "delivery_charges": None,
            "ratings": None,
            "reviews": self.reviews(product),
            "images": self.images(product),
            "url": None,
            "source": "Daraz",
            "scraped_at": datetime.datetime.now()
        }

if __name__ == "__main__":
    search_query = input("Enter the product name : ").strip()
    if not search_query:
        print("Search query cannot be empty.")
        exit()
    
    collection_name = input("Enter the db_collection name: ").strip()
    while not collection_name:
        print("Please Enter Your collection name for further continue.")
        collection_name = input("Enter the db_collection name: ").strip()
    while collection_name in pymongo.MongoClient("mongodb://localhost:27017/")["daraz_db"].list_collection_names():
        print(f"Same db_collection '{collection_name}' already exists. Please enter a new db_collection name.")
        collection_name = input("Enter a new db_collection name: ").strip()
       

    scraper = DarazScraper(search_query, collection_name)
    scraper.run()