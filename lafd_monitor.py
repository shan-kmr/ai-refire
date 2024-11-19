import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re

class LAFDAlertMonitor:
    def __init__(self):
        """Initialize LAFD Alert Monitor"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def parse_alert_body(self, body_text):
        """Parse the structured alert body text"""
        try:
            # Split main components by semicolon
            parts = [part.strip() for part in body_text.split(';')]

            # Extract basic info from first parts
            incident_type = parts[0]
            incident_number = parts[1].strip() if len(parts) > 1 else ''

            # Extract time and address
            time = ''
            address = ''
            if len(parts) > 2:
                time_match = re.search(r'(\d{1,2}:\d{2}(?:AM|PM))', parts[2])
                if time_match:
                    time = time_match.group(1)
                # Address is typically after the time
                address_parts = parts[2].split(';')[0].split(time)
                if len(address_parts) > 1:
                    address = address_parts[1].strip()

            # Extract neighborhood if present
            neighborhood = parts[3].strip() if len(parts) > 3 else ''

            # Extract main description (usually the longest part)
            description = ''
            for part in parts:
                if len(part.strip()) > 50:  # Likely the main description
                    description = part.strip()
                    break

            return {
                'incident_type': incident_type,
                'incident_number': incident_number,
                'time': time,
                'address': address,
                'neighborhood': neighborhood,
                'description': description
            }
        except Exception as e:
            return {
                'incident_type': body_text,
                'incident_number': '',
                'time': '',
                'address': '',
                'neighborhood': '',
                'description': ''
            }

    def get_alerts(self):
        """Get latest alerts from LAFD website"""
        alerts = []
        try:
            response = requests.get('https://lafd.org/alerts', headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find alert items
            alert_items = soup.find_all('div', class_='views-row')

            for item in alert_items:
                try:
                    # Extract title and link
                    title_elem = item.find('h2', class_='alert-node-title')
                    if not title_elem:
                        continue

                    link_elem = title_elem.find('a')
                    title = link_elem.text.strip()
                    link = 'https://lafd.org' + link_elem['href']

                    # Extract body content
                    body_elem = item.find('div', class_='alert-node-body')
                    body_text = body_elem.text.strip() if body_elem else ''

                    # Parse structured information from body
                    parsed_info = self.parse_alert_body(body_text)

                    # Extract date from title or incident number
                    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', title)
                    date_str = date_match.group(1) if date_match else None

                    if date_str and parsed_info['time']:
                        datetime_str = f"{date_str} {parsed_info['time']}"
                        try:
                            date = pd.to_datetime(datetime_str, format='%m/%d/%Y %I:%M%p')
                        except:
                            date = pd.to_datetime(date_str)
                    else:
                        date = pd.Timestamp.now()

                    alerts.append({
                        'date': date,
                        'title': title,
                        'incident_type': parsed_info['incident_type'],
                        'incident_number': parsed_info['incident_number'],
                        'address': parsed_info['address'],
                        'neighborhood': parsed_info['neighborhood'],
                        'description': parsed_info['description'],
                        'link': link
                    })

                except Exception as e:
                    continue

        except Exception as e:
            print(f"Error fetching LAFD alerts: {e}")

        return pd.DataFrame(alerts)

    def show_latest(self, max_items=10):
        """Display latest LAFD alerts"""
        df = self.get_alerts()

        if df.empty:
            print("No recent LAFD alerts found")
            return

        # Sort by date
        df = df.sort_values('date', ascending=False)

        print("\nLatest LAFD Alerts")
        print("=" * 80)

        for _, alert in df.head(max_items).iterrows():
            print(f"\nTime: {alert['date'].strftime('%Y-%m-%d %I:%M %p')}")
            print(f"Type: {alert['incident_type']}")
            print(f"Number: {alert['incident_number']}")
            if alert['address']:
                print(f"Location: {alert['address']}")
            if alert['neighborhood']:
                print(f"Neighborhood: {alert['neighborhood']}")
            if alert['description']:
                print(f"Details: {alert['description']}")
            print(f"Link: {alert['link']}")
            print("-" * 80)

def monitor_alerts():
    monitor = LAFDAlertMonitor()
    monitor.show_latest()

if __name__ == "__main__":
    monitor_alerts()