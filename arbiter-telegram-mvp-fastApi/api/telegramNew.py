from api.models import SentimentAnalyser, ToxicityAnalyser, EmotionAnalyser
from datetime import datetime
from bs4 import BeautifulSoup
from nomic import atlas
import pandas as pd
import requests
import logging
import nomic
import time
import re
from typing import List, Dict, Optional


class Telegram:
    sentiment_pipeline = SentimentAnalyser()
    toxicity_pipeline = ToxicityAnalyser()
    emotion_pipeline = EmotionAnalyser()

    def __init__(self, search_phrase: str, google_cse_api_key: str, nomic_api_key: str):
        self.search_phrase = search_phrase
        self.google_api_key = google_cse_api_key
        nomic.login(token=nomic_api_key)
        self.df: Optional[pd.DataFrame] = None

    def get_search_results(self, i: int) -> Optional[List[Dict]]:
        base_url = (
            f"https://customsearch.googleapis.com/customsearch/v1?key={self.google_api_key}"
            f"&cx=30154c4e98fbe4923&q={self.search_phrase.strip().replace(' ', '+')}&start={i}"
        )
        base_url = (f"https://cse.google.com/cse/element/v1?start={i}&cx=006249643689853114236%3Aa3iibfpwexa&q={self.search_phrase.strip().replace(' ', '+')}&cse_tok={self.google_api_key}&callback=google.search.cse.api10362")
        try:
            response = requests.get(base_url)
            response.raise_for_status()
            json_data = response.text.strip("/*O_o*/\ngoogle.search.cse.api10362(").rstrip(");")
            res = json_data.json()
            return res.get('items', [])
        except requests.RequestException as e:
            logging.error(f"Error fetching search results: {e}")
            return None

    def extract_formatted_urls(self, items: List[Dict]) -> set:
        return {item.get('link') for item in items if 'link' in item}

    def extract_channel_name(self, url: str) -> Optional[str]:
        match = re.search(r't\.me/(?:s/)?([a-zA-Z0-9_]+)', url)
        return match.group(1) if match else None

    def get_channel_names(self) -> List[str]:
        all_channel_names = set()
        for start in range(0, 100, 10):
            logging.info(f"Fetching results starting from index {start}...")
            items = self.get_search_results(start)
            if not items:
                break
            links = self.extract_formatted_urls(items)
            for url in links:
                channel_name = self.extract_channel_name(url)
                if channel_name:
                    all_channel_names.add(
                        f"https://t.me/s/{channel_name}?q={self.search_phrase.strip().replace(' ', '+')}"
                    )
        return list(all_channel_names)

    def get_unique_hrefs_from_channel(self, url: str) -> List[str]:
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', class_='tgme_widget_message_date')
            return [link.get('href') for link in links if link.get('href')]
        except requests.RequestException as e:
            logging.error(f"Error fetching Telegram channel page: {e}")
            return []

    def get_all_hrefs_from_channels(self, all_channel_names: List[str]) -> List[str]:
        all_hrefs = []
        for url in all_channel_names:
            all_hrefs.extend(self.get_unique_hrefs_from_channel(url))
        return list(set(all_hrefs))

    def scrape_engagement_metrics(self, url: str) -> Optional[Dict]:
        try:
            response = requests.get(f"{url}?embed=1&mode=tme")
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            content_div = soup.find("div", class_="tgme_widget_message_text")
            metadata_div = soup.find("time", class_="datetime")
            engagement_div = soup.find("span", class_="tgme_widget_message_views")

            return {
                "link": url,
                "text": content_div.get_text(strip=True) if content_div else " ",
                "group": self.extract_channel_name(url) or " ",
                "date": metadata_div.get_text(strip=True) if metadata_div else " ",
                "views": engagement_div.get_text(strip=True) if engagement_div else None,
            }
        except requests.RequestException as e:
            logging.error(f"Error fetching metrics from {url}: {e}")
            return None

    def get_data(self):
        channel_names = self.get_channel_names()
        if not channel_names:
            logging.warning("No channels found.")
            return

        all_hrefs = self.get_all_hrefs_from_channels(channel_names)
        data = []
        for href in all_hrefs:
            metrics = self.scrape_engagement_metrics(href)
            if metrics:
                data.append(metrics)
        self.df = pd.DataFrame(data)

    def _parse_time_of_post(self, time_string: str) -> datetime:
        try:
            return datetime.strptime(time_string, "%b %d, %Y at %H:%M")
        except ValueError:
            current_year = datetime.now().year
            return datetime.strptime(f"{time_string}, {current_year}", "%b %d at %H:%M, %Y")

    def _convert_views_to_number(self, views_str: str) -> Optional[float]:
        try:
            if 'K' in views_str:
                return float(views_str.replace('K', '')) * 1_000
            elif 'M' in views_str:
                return float(views_str.replace('M', '')) * 1_000_000
            return float(views_str)
        except ValueError:
            return None

    def generate_insights(self) -> Dict:
        if self.df is None or self.df.empty:
            logging.warning("No data to analyze.")
            return {}

        self.df['views'] = self.df['views'].apply(self._convert_views_to_number)
        self.df['date'] = self.df['date'].apply(self._parse_time_of_post)
        self.df['date'] = pd.to_datetime(self.df['date'], unit='s').dt.normalize()

        insights = {
            "platform": "telegram",
            "general": self._get_general_analytics(),
            "text_analysis": self._get_text_analysis(),
        }
        return insights

    def _get_general_analytics(self) -> Dict:
        engagement_distribution = self.df.groupby(['date']).agg({'views': 'sum'}).reset_index()
        engagement_distribution.rename(columns={'views': 'engagement'}, inplace=True)

        top_channels_posts = self.df['group'].value_counts().head(15).reset_index()
        top_channels_posts.columns = ['group', 'posts']

        top_channels_views = self.df.groupby('group')['views'].sum().nlargest(15).reset_index()
        top_channels_views.columns = ['group', 'engagement']

        return {
            "metrics": [
                {"title": "Total Messages", "metric": len(self.df)},
                {"title": "Total Views", "metric": int(self.df['views'].sum())},
                {"title": "Total Channels", "metric": self.df['group'].nunique()},
            ],
            "engagement_distribution": engagement_distribution.to_dict(orient='records'),
            "group_posts_distribution": top_channels_posts.to_dict(orient='records'),
            "group_engagement_distribution": top_channels_views.to_dict(orient='records'),
        }

    def _get_text_analysis(self) -> dict:
        self.df['text'] = self.df['text'].apply(lambda x: x[:512])

        sentiment_time = time.time()
        self.df['sentiment'] = Telegram.analyse_sentiment(self.df['text'].tolist())
        self.df['sentiment'] = self.df['sentiment'].apply(lambda x: x['label'])
        logging.info("sentiment time: %.2f seconds", time.time() - sentiment_time)

        emotion_time = time.time()
        self.df['emotion'] = Telegram.analyse_emotion(self.df['text'].tolist())
        self.df['emotion'] = self.df['emotion'].apply(lambda x: x['label'])
        logging.info("emotion time: %.2f seconds", time.time() - emotion_time)

        def assign_toxicity_label(preds, threshold=0.1, difference_threshold=0.1):
            sorted_preds = sorted(preds, key=lambda x: x['score'], reverse=True)
            max_label, max_score = sorted_preds[0]['label'], sorted_preds[0]['score']

            if max_score < threshold:
                return 'non_toxic'

            second_label, second_score = sorted_preds[1]['label'], sorted_preds[1]['score']
            if (max_score - second_score) < difference_threshold:
                return second_label

            return max_label

        toxicity_time = time.time()
        self.df['toxicity'] = Telegram.analyse_toxicity(self.df['text'].tolist())
        self.df['toxicity'] = self.df['toxicity'].apply(assign_toxicity_label)
        logging.info('toxicity time: %.2f seconds', time.time() - toxicity_time)

        try:
            dataset_time = time.time()
            dataset = atlas.map_data(
                data=self.df.reset_index(),
                indexed_field='text',
                identifier=f'sm8523/arbiter-telegram-{self.search_phrase}',
                description=f'arbiter-telegram-{self.search_phrase}',
                duplicate_detection=True
            )
            logging.info('dataset time: %.2f seconds', time.time() - dataset_time)
            dataset_link = f"{dataset.identifier}/map/{dataset.maps[0].id}"
        except Exception as e:
            dataset_link = None
            logging.error(e)
            logging.info(f"nomic dataset process failed for {self.search_phrase}")

        sentiment_distribution = self.df.groupby(['sentiment'])['sentiment'].count().reset_index(name='posts')
        emotion_distribution = self.df.groupby(['emotion'])['emotion'].count().reset_index(name='posts')
        toxicity_distribution = self.df.groupby(['toxicity'])['toxicity'].count().reset_index(name='posts')

        return {
            "sentiment_analysis": sentiment_distribution.to_dict(orient='records'),
            "emotion_analysis": emotion_distribution.to_dict(orient='records'),
            "toxicity_analysis": toxicity_distribution.to_dict(orient='records'),
            "nomic_visualization": dataset_link
        }

    @staticmethod
    def analyse_sentiment(text: str | list) -> dict:
        result = Telegram.sentiment_pipeline.predict(text)
        return result

    @staticmethod
    def analyse_toxicity(text: str | list) -> dict:
        result = Telegram.toxicity_pipeline.predict(text)
        return result

    @staticmethod
    def analyse_emotion(text: str | list) -> dict:
        result = Telegram.emotion_pipeline.predict(text)
        return result
