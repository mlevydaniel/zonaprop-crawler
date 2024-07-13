import requests
from bs4 import BeautifulSoup
import json
import re
import time

def safe_extract(element, selector, attribute=None):
    found = element.select_one(selector)
    if not found:
        return None
    if attribute:
        return found.get(attribute)
    return found.get_text(strip=True)

def scrape_zonaprop_page(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    listings = []

    # Find all listing containers
    listing_containers = soup.find_all('div', class_='PostingCardLayout-sc-i1odl-0')

    print(f"Found {len(listing_containers)} listings on this page")

    for listing in listing_containers:
        try:
            # Extract data using the safe_extract function
            title = safe_extract(listing, 'h2.postingCard-title')
            price = safe_extract(listing, 'div[data-qa="POSTING_CARD_PRICE"]')
            expenses = safe_extract(listing, 'div[data-qa="expensas"]')
            location_address = safe_extract(listing, 'div.postingAddress')
            location_area = safe_extract(listing, 'h2[data-qa="POSTING_CARD_LOCATION"]')

            features_div = listing.find('h3', class_='PostingMainFeaturesBlock-sc-1uhtbxc-0')
            features = [span.text.strip() for span in features_div.find_all('span')] if features_div else []

            description = safe_extract(listing, 'h3[data-qa="POSTING_CARD_DESCRIPTION"]')

            url_element = listing.find('a', href=True)
            url = f"https://www.zonaprop.com.ar{url_element['href']}" if url_element else None

            # Extract property type and operation type from the URL
            property_type = "Unknown"
            operation_type = "Unknown"
            if url:
                url_parts = url.split('/')
                if len(url_parts) > 3:
                    property_operation = url_parts[3].split('-')
                    if len(property_operation) > 1:
                        property_type = property_operation[0]
                        operation_type = property_operation[1]

            listings.append({
                'title': title,
                'price': price,
                'expenses': expenses,
                'location_address': location_address,
                'location_area': location_area,
                'features': features,
                'description': description,
                'url': url,
                'property_type': property_type,
                'operation_type': operation_type
            })
        except Exception as e:
            print(f"Error parsing a listing: {e}")

    # Find the next page
    current_page = int(re.search(r'PAGING_(\d+)', str(soup)).group(1))
    next_page = soup.find('a', attrs={'data-qa': f'PAGING_{current_page + 1}'})
    next_page_url = f"https://www.zonaprop.com.ar{next_page['href']}" if next_page else None

    return listings, next_page_url

def scrape_zonaprop(start_url, max_pages=None):
    all_listings = []
    current_url = start_url
    page_num = 1

    while current_url:
        print(f"Scraping page {page_num}...")
        page_listings, next_page_url = scrape_zonaprop_page(current_url)
        all_listings.extend(page_listings)

        if max_pages and page_num >= max_pages:
            print(f"Reached maximum number of pages ({max_pages})")
            break

        current_url = next_page_url
        page_num += 1

        # Add a delay to avoid overloading the server
        time.sleep(2)

    return all_listings

def main():
    start_url = 'https://www.zonaprop.com.ar/casas-departamentos-ph-alquiler-caballito.html'
    listings = scrape_zonaprop(start_url, max_pages=1)  # Limit to 1 pages for this example

    if listings:
        with open('zonaprop_caballito_rentals.json', 'w', encoding='utf-8') as f:
            json.dump(listings, f, ensure_ascii=False, indent=4)
        print(f"Scraped {len(listings)} listings and saved to zonaprop_caballito_rentals.json")
    else:
        print("No listings were found or scraped.")

if __name__ == "__main__":
    main()
