import requests
import random
import time
from urllib.parse import quote
from typing import Dict, List, Optional
import certifi

import requests
import json
from geopy.geocoders import Nominatim

def find_closest_city(latitude, longitude):
    geolocator = Nominatim(user_agent="myGeocoder")
    location = geolocator.reverse(f"{latitude}, {longitude}")

    if location:
        address = location.raw['address']
        city = address.get('city', address.get('town', address.get('village', 'Unknown')))
        return city
    else:
        return "Unknown"

def search_reddit(query):
    url = f"https://www.reddit.com/search.json?q={query}"
    response = requests.get(url, headers={'User-Agent': 'MyBot/1.0'})
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        return None

# Example usage

latitude = 34.0549
longitude = -118.2426

closest_city = find_closest_city(latitude, longitude)
print(f"The closest city to coordinates ({latitude}, {longitude}) is: {closest_city}")

class RedditCityScraper:
    def __init__(self):
        # self.cities = [
        #     "tokyo", "paris", "london", "newyork", "singapore",
        #     "berlin", "sydney", "toronto", "dubai", "seoul"
        # ]
        self.cities = [find_closest_city(latitude, longitude)]

        # Base URL for OAuth endpoint
        self.base_url = "https://oauth.reddit.com"

        # Your Reddit API credentials
        self.client_id = "OX9cHbc51DNkrWSpgFNWkA"
        self.client_secret = "rkmMR7I2CS65PxPg4Q_ZqGhPizlWZA"

        # Get the OAuth token
        self.access_token = self._get_access_token()

        # Headers with OAuth token
        self.headers = {
            'User-Agent': 'Python:CitySearchBot:v1.0 (by /u/Inside-Advisor-7840)',
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }

    def _get_access_token(self) -> str:
        """
        Get OAuth access token from Reddit
        """
        auth_url = "https://www.reddit.com/api/v1/access_token"
        auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)

        headers = {
            'User-Agent': 'Python:CitySearchBot:v1.0 (by /u/Inside-Advisor-7840)'
        }

        data = {
            'grant_type': 'client_credentials'
        }

        try:
            response = requests.post(
                auth_url,
                auth=auth,
                headers=headers,
                data=data,
                verify=certifi.where()  # Use certifi for SSL verification
            )
            response.raise_for_status()

            return response.json()['access_token']

        except requests.RequestException as e:
            print(f"Error getting access token: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response text: {e.response.text}")
            raise

    def search_city(self, city: str) -> Optional[Dict]:
        """
        Search Reddit for posts about a specific city using OAuth.
        """
        # Encode the city name for URL
        encoded_city = quote(city)

        # Construct search URL
        search_url = f"{self.base_url}/search"

        params = {
            'q': encoded_city,
            'limit': 25,
            'sort': 'comments',
            'raw_json': 1
        }

        try:
            # Add delay to respect rate limits
            time.sleep(2)

            response = requests.get(
                search_url,
                headers=self.headers,
                params=params,
                verify=certifi.where(),  # Use certifi for SSL verification
                timeout=10
            )
            # print(search_url)

            print(f"Status Code: {response.status_code}")
            response.raise_for_status()

            return response.json()

        except requests.RequestException as e:
            print(f"Error searching for {city}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response text: {e.response.text}")
            return None

    def process_results(self, data: Dict) -> List[Dict]:
        """
        Extract relevant information from Reddit search results.
        """
        posts = []

        try:
            for child in data['data']['children']:
                post = child['data']
                posts.append({
                    'title': post.get('title'),
                    'subreddit': post.get('subreddit'),
                    'score': post.get('score'),
                    'url': f"https://reddit.com{post.get('permalink')}",
                    'created_utc': post.get('created_utc'),
                    'num_comments': post.get('num_comments'),
                    'author': post.get('author')
                })
        except KeyError as e:
            print(f"Error processing results: {str(e)}")

        return posts

    def get_random_city_data(self) -> List[Dict]:
        """
        Search for a random city from the predefined list.
        """
        city = random.choice(self.cities)
        print(f"Searching for city: {city}")

        results = self.search_city(city)
        if results:
            return self.process_results(results)
        return []

def main():
    try:
        scraper = RedditCityScraper()
        posts = scraper.get_random_city_data()

        # Print the results
        for i, post in enumerate(posts[:5], 1):
            print(f"\nPost {i}:")
            print(f"Title: {post['title']}")
            print(f"Subreddit: r/{post['subreddit']}")
            print(f"Score: {post['score']}")
            print(f"Comments: {post['num_comments']}")
            print(f"Author: u/{post['author']}")
            print(f"URL: {post['url']}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()