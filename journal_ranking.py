import argparse
import requests
from bs4 import BeautifulSoup
import time
import re

def get_journal_categories(journal_name):
    """
    Finds a journal's SCImago profile and lists its categories and recent quartiles.
    
    Args:
        journal_name (str): The name of the journal to search for.
        
    Returns:
        dict: Journal details including a list of categories and their latest Q-rating.
    """
    # 1. Search for the journal to get the profile URL
    search_url = "https://www.scimagojr.com/journalsearch.php"
    params = {"q": journal_name}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    print(f"Searching for '{journal_name}'...")
    
    try:
        resp = requests.get(search_url, params=params, headers=headers)
        soup = BeautifulSoup(resp.content, "html.parser")
        
        # The search result list
        search_results = soup.find_all("div", class_="search_results")
        
        journal_link = None
        real_title = None
        
        # Loop to find the first valid journal link
        if search_results:
            # Usually the first result is the best match
            first_result = search_results[0].find("a")
            if first_result:
                journal_link = first_result['href']
                real_title = first_result.find("span", class_="jrnlname").get_text(strip=True)
        
        if not journal_link:
            print("Journal not found.")
            return None

        # Fix relative URL if necessary
        if not journal_link.startswith("http"):
            journal_link = "https://www.scimagojr.com/" + journal_link
            
        print(f"Found profile: {real_title}")
        # print(f"URL: {journal_link}")

        # 2. Go to the specific journal profile page
        profile_resp = requests.get(journal_link, headers=headers)
        profile_soup = BeautifulSoup(profile_resp.content, "html.parser")
        
        # 3. Extract Categories
        # Structure: <a>Category Name</a>
        categories_data = []
        cat_links = profile_soup.find_all("a",
                                          href=lambda href: href and "journalrank.php?category=" in href)
        
        category_map = {}
        for link in cat_links:
            cat_name = link.get_text(strip=True)
            # Extract category ID from href (e.g., ...?category=1702)
            match = re.search(r"category=(\d+)", link['href'])
            cat_id = match.group(1) if match else "Unknown"
            
            # Avoid duplicates (sometimes appear twice)
            if cat_id not in category_map:
                category_map[cat_id] = cat_name

        # 4. Extract Quartiles (The colorful grid)
        print("\n--- Categories and Recent Quartiles ---")
        for cat_id, cat_name in category_map.items():
            print(f"Category: {cat_name} (ID: {cat_id})")
            categories_data.append({"name": cat_name, "id": cat_id})

        return {"journal": real_title, "categories": categories_data, "url": journal_link}

    except Exception as e:
        print(f"Error: {e}")
        return None

def get_total_journals(soup):
    """
    Robustly finds the total number of journals.
    Method 1: Check 'total_size' parameter in pagination links.
    Method 2: Check max page number in pagination * 50.
    """
    
    # 1. Look for 'total_size=' in any link on the page
    # This is often hidden in the 'Next' or 'Last' buttons
    all_links = soup.find_all("a", href=True)
    max_total_size = 0
    
    for link in all_links:
        href = link['href']
        match = re.search(r"total_size=(\d+)", href)
        if match:
            val = int(match.group(1))
            if val > max_total_size:
                max_total_size = val
    
    if max_total_size > 0:
        return max_total_size

    # 2. Fallback: Find max page number in pagination
    # Usually in a div, but we can just look for links with 'page='
    max_page = 0
    for link in all_links:
        href = link['href']
        match = re.search(r"page=(\d+)", href)
        if match:
            page_num = int(match.group(1))
            if page_num > max_page:
                max_page = page_num
    
    if max_page > 0:
        # Estimate based on last page
        return max_page * 50

    return None

def get_total_journal_old(soup):
    """
    Attempts to find the total number of journals in the category.
    """
    # Strategy: Text search for "1 - ?? of 2300"
    # This text often appears in the .journalrank-header or similar
    body_text = soup.get_text()
    # print(body_text)
    match = re.search(r"1\s*-\s*\d\d\s*of\s*(\d+)", body_text)
    if match:
        return int(match.group(1))

    return None

def get_scimago_ranking(journal_name, category_id, year):
    """
    Finds the rank and quartile of a journal within a specific SCImago category.
    
    Args:
        journal_name (str): The name of the journal to find (case-insensitive).
        category_id (int): The SCImago category ID (e.g., 1702 for Artificial Intelligence).
        
    Returns:
        dict: A dictionary containing 'Rank', 'Quartile', and 'Category', or
        None if not found.
    """
    base_url = "https://www.scimagojr.com/journalrank.php"
    page = 1
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    print(f"Searching for '{journal_name}' in Category ID: {category_id}...")

    while True:
        # Construct the URL for the specific category and page
        year_param = f"&year={year}" if year else ""
        url = f"{base_url}?category={category_id}&page={page}{year_param}"
        print(url)
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Error fetching page {page}: Status {response.status_code}")
                break
                
            soup = BeautifulSoup(response.content, "html.parser")

            # Get total number of journals
            number_journals = get_total_journals(soup)
            
            # SCImago tables are usually standard HTML tables
            table_rows = soup.find_all("tr")
            
            # If no rows (except header), we've reached the end
            if len(table_rows) <= 1: 
                break
                
            # Iterate through rows (skipping header if necessary)
            for row in table_rows:
                # The title is usually in an anchor tag within the row
                title_tag = row.find("a", title="view journal details")
                if title_tag:
                    curr_journal_title = title_tag.get_text(strip=True)
                    
                    # Check for partial or exact match
                    if journal_name.lower() in curr_journal_title.lower():
                        # Extract Rank: usually the first column text
                        cols = row.find_all("td")
                        rank = cols[0].get_text(strip=True)
                        
                        # Extract Quartile: Look for a span/div with class
                        # 'q1', 'q2', etc.
                        quartile = "N/A"
                        for q_class in ['q1', 'q2', 'q3', 'q4']:
                            if row.find(class_=q_class):
                                quartile = q_class.upper()
                                break
                        
                        return {
                            "Journal": curr_journal_title,
                            "Rank": rank,
                            "Number journals": number_journals,
                            "Quartile": quartile,
                            "Category ID": category_id,
                            "Page Found": page
                        }
            
            # Check if there is a 'Next' button to continue; otherwise, safety break
            pagination = soup.find("div", class_="pagination")
            if not pagination or "Next" not in pagination.get_text():
                 # Sometimes pagination is just page numbers; scraping blindly
                 # until empty is safer
                 pass
            
            print(f"Checked page {page}...")
            page += 1
            time.sleep(1) # Be polite to the server
            
            if page > 100: # Safety break to prevent infinite loops
                print("Reached page limit (100). Journal not found.")
                break
                
        except Exception as e:
            print(f"An error occurred: {e}")
            break

    return None

if __name__ == "__main__":
    # Initialize Argument Parser
    parser = argparse.ArgumentParser(description="Get SCImago rankings for a specific journal.")
    
    # Add argument for journal name
    parser.add_argument("journal_name",
                        type=str,
                        help="The name of the journal (use quotes if it has spaces)")
    parser.add_argument("--year", "-y", type=str, help="Year (e.g., 2018)", default=None)
    parser.add_argument("--category", "-c", type=int, help="Journal Category (e.g., 2210)", default=None)
    
    # Parse arguments
    args = parser.parse_args()
    
    # get journal category
    if args.category is None:
        get_journal_categories(args.journal_name)
        category_id = int(input("\nChoose journal category: "))
        print()
    else:
        category_id = args.category

    # Run the main function
    result = get_scimago_ranking(args.journal_name, category_id, args.year)

    if result:
        print("\n--- Result Found ---")
        print(f"Journal: {result['Journal']}")
        print(f"Category Rank: #{result['Rank']} of {result['Number journals']}")
        print(f"Percentile: {100*int(result['Rank'])/result['Number journals']:.2f}%")
        print(f"Quartile: {result['Quartile']}")
    else:
        print("\nJournal not found in this category.")
