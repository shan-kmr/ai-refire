!pip install feedparser
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import re
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import feedparser
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

class FireIncidentAnalyzer:
    def __init__(self):
        """Initialize the fire incident severity analyzer"""
        self.severity_keywords = {
            'critical': ['major', 'massive', 'explosive', 'evacuation', 'multiple alarm', 'deaths',
                        'fatalities', 'catastrophic', 'out of control'],
            'high': ['large', 'spreading', 'structural', 'injuries', 'homes threatened',
                    'buildings damaged', 'widespread'],
            'medium': ['contained', 'under control', 'brush fire', 'vehicle fire',
                      'limited damage', 'minor injuries'],
            'low': ['small', 'controlled', 'extinguished', 'minor', 'no injuries',
                   'quickly contained']
        }

    def classify_severity(self, text):
        """
        Classify the severity of a fire incident based on article text

        Returns:
        tuple: (severity_level, confidence_score)
        """
        text_lower = text.lower()
        scores = {level: 0 for level in self.severity_keywords.keys()}

        # Count keyword matches for each severity level
        for level, keywords in self.severity_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[level] += 1

        # Calculate severity level and confidence
        max_score = max(scores.values())
        if max_score == 0:
            return ('unknown', 0.0)

        severity = max(scores.items(), key=lambda x: x[1])[0]
        confidence = max_score / len(self.severity_keywords[severity])

        return (severity, round(confidence, 2))

class LocationManager:
    def __init__(self):
        """Initialize the location manager with geocoding capability"""
        self.geolocator = Nominatim(user_agent="fire_monitor")
        self.location_cache = {}

    def get_coordinates(self, location_str):
        """Get coordinates for a location string with caching"""
        if location_str in self.location_cache:
            return self.location_cache[location_str]

        try:
            location = self.geolocator.geocode(location_str)
            if location:
                coords = (location.latitude, location.longitude)
                self.location_cache[location_str] = coords
                return coords
        except Exception as e:
            print(f"Geocoding error for {location_str}: {e}")

        return None

    def calculate_distance(self, location1, location2):
        """Calculate distance between two locations in miles"""
        coords1 = self.get_coordinates(location1)
        coords2 = self.get_coordinates(location2)

        if coords1 and coords2:
            return round(geodesic(coords1, coords2).miles, 1)
        return None

class FireDepartmentFeed:
    def __init__(self):
        """Initialize fire department feed parser"""
        # List of common fire department RSS feeds
        self.feed_urls = {
            'Los Angeles': 'https://www.lafd.org/alerts',
            'San Francisco': 'https://sf-fire.org/rss',
            # Add more fire department feeds as needed
        }

    def get_department_updates(self, city):
        """Get updates from fire department feed for specified city"""
        if city not in self.feed_urls:
            return pd.DataFrame()

        try:
            feed = feedparser.parse(self.feed_urls[city])
            updates = []

            for entry in feed.entries:
                updates.append({
                    'Title': entry.title,
                    'Source': f"{city} Fire Department",
                    'Date': datetime.fromtimestamp(time.mktime(entry.published_parsed)),
                    'Link': entry.link,
                    'Content': entry.description if 'description' in entry else ''
                })

            return pd.DataFrame(updates)
        except Exception as e:
            print(f"Error fetching fire department feed for {city}: {e}")
            return pd.DataFrame()

class EnhancedFireNewsMonitor:
    def __init__(self, city, radius_miles=50):
        """
        Initialize enhanced fire news monitor

        Parameters:
        city (str): Primary city to monitor
        radius_miles (int): Radius in miles to monitor around the city
        """
        self.city = city
        self.radius_miles = radius_miles
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.known_articles = set()
        self.location_manager = LocationManager()
        self.incident_analyzer = FireIncidentAnalyzer()
        self.department_feed = FireDepartmentFeed()

    def get_nearby_cities(self):
        """Get list of major cities within specified radius"""
        # This would ideally use a geographic database
        # For now, returning a simplified list of nearby major cities
        major_cities = {
            'San Francisco': ['Oakland', 'San Jose', 'Berkeley'],
            'Los Angeles': ['Long Beach', 'Pasadena', 'Glendale'],
            # Add more city relationships as needed
        }
        return major_cities.get(self.city, [])

    def search_fire_news(self, include_nearby=True):
        """
        Search for fire-related news with enhanced filtering and analysis

        Parameters:
        include_nearby (bool): Include news from nearby cities within radius

        Returns:
        pandas.DataFrame: Analyzed and filtered fire incident news
        """
        all_articles = []
        search_locations = [self.city]

        if include_nearby:
            search_locations.extend(self.get_nearby_cities())

        # Get fire department updates
        dept_updates = self.department_feed.get_department_updates(self.city)
        if not dept_updates.empty:
            all_articles.extend(dept_updates.to_dict('records'))

        # Search news for each location
        for location in search_locations:
            query = f"fire {location}".replace(' ', '+')
            url = f"https://news.google.com/search?q={query}&hl=en-US&gl=US&ceid=US:en"

            try:
                response = requests.get(url, headers=self.headers)
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.find_all('article', class_='MQsxIb')

                for article in articles:
                    try:
                        title = article.find('h3').text.strip()
                        source = article.find('div', class_='UPmit').text.strip()
                        date = article.find('time')['datetime']
                        link = 'https://news.google.com' + article.find('a')['href'][1:]

                        article_id = f"{title}:{source}"

                        if article_id not in self.known_articles:
                            # Calculate distance from primary city
                            distance = self.location_manager.calculate_distance(self.city, location)

                            if distance is None or distance <= self.radius_miles:
                                # Analyze severity
                                severity, confidence = self.incident_analyzer.classify_severity(title)

                                self.known_articles.add(article_id)
                                all_articles.append({
                                    'Title': title,
                                    'Source': source,
                                    'Date': pd.to_datetime(date),
                                    'Link': link,
                                    'Location': location,
                                    'Distance': distance,
                                    'Severity': severity,
                                    'Confidence': confidence
                                })

                    except Exception as e:
                        continue

            except Exception as e:
                print(f"Error fetching news for {location}: {e}")
                continue

        # Create and process DataFrame
        news_df = pd.DataFrame(all_articles)
        if not news_df.empty:
            # Sort by severity and date
            severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'unknown': 4}
            news_df['severity_rank'] = news_df['Severity'].map(severity_order)
            news_df = news_df.sort_values(['severity_rank', 'Date'],
                                        ascending=[True, False]).drop('severity_rank', axis=1)

        return news_df

    def monitor_fires(self, interval_minutes=5, duration_hours=None, min_severity='low'):
        """
        Enhanced continuous monitoring of fire incidents

        Parameters:
        interval_minutes (int): Check frequency
        duration_hours (float): Monitor duration (None for indefinite)
        min_severity (str): Minimum severity level to report
        """
        start_time = datetime.now()
        severity_levels = ['critical', 'high', 'medium', 'low']
        min_severity_index = severity_levels.index(min_severity)

        print(f"Starting enhanced fire monitoring for {self.city} and surrounding {self.radius_miles} mile radius")
        print(f"Minimum severity level: {min_severity}")
        print("Press Ctrl+C to stop monitoring")

        try:
            while True:
                if duration_hours and (datetime.now() - start_time).total_seconds() / 3600 >= duration_hours:
                    break

                print(f"\nChecking for fire incidents... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                new_articles = self.search_fire_news()

                if not new_articles.empty:
                    # Filter by severity
                    filtered_articles = new_articles[
                        new_articles['Severity'].apply(lambda x:
                            severity_levels.index(x) <= min_severity_index if x in severity_levels else False)
                    ]

                    if not filtered_articles.empty:
                        print(f"\nFound {len(filtered_articles)} relevant fire incidents:")
                        for _, article in filtered_articles.iterrows():
                            print(f"\nTitle: {article['Title']}")
                            print(f"Location: {article['Location']}")
                            if article['Distance']:
                                print(f"Distance: {article['Distance']} miles from {self.city}")
                            print(f"Severity: {article['Severity'].upper()} (Confidence: {article['Confidence']})")
                            print(f"Source: {article['Source']}")
                            print(f"Date: {article['Date']}")
                            print(f"Link: {article['Link']}")
                            print("-" * 80)
                    else:
                        print(f"No new incidents meeting minimum severity threshold: {min_severity}")
                else:
                    print("No new fire incidents found")

                time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")

        print("Monitoring session ended")

def example_usage():
    # Example monitoring for fire incidents
    monitor = EnhancedFireNewsMonitor("Los Angeles", radius_miles=300)

    # Option 1: Get current incidents
    current_incidents = monitor.search_fire_news()
    print("Current Incidents:")
    print(current_incidents)

    # Option 2: Monitor continuously
    monitor.monitor_fires(
        interval_minutes=0.5,
        duration_hours=36,
        min_severity='low'
    )

if __name__ == "__main__":
    example_usage()