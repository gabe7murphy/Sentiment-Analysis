from urllib.request import urlopen
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from newAnalyzer import SentimentIntensityAnalyzer 
import time
import pprint

def my_scraper():
    date_sentiments = {}
    unique_dates = set()
    for i in range(1,30):
        page = urlopen('https://www.businesstimes.com.sg/search/state%20street?page='+str(i)).read()
        soup = BeautifulSoup(page, features="html.parser")
        posts = soup.findAll("div", {"class": "media-body"})
        for post in posts:
    #        post = posts[0]
            time.sleep(0.1)
            url = post.a['href']
            date = post.time.text
            unique_dates.add(date)
            print(date, url)
            try:
                link_page = urlopen(url).read()
            except:
                url = url[:-2]
                link_page = urlopen(url).read()
            link_soup = BeautifulSoup(link_page)
            sentences = link_soup.findAll("p")
            passage = ""
            for sentence in sentences:
                passage += sentence.text
            sia = SentimentIntensityAnalyzer()
            sentiment = sia.polarity_scores(passage)['compound']
            date_sentiments.setdefault(date, []).append(sentiment)

    date_sentiment = {}

    for k,v in date_sentiments.items():
        date_sentiment[datetime.strptime(k, '%d %b %Y').date() + timedelta(days=1)] = round(sum(v)/float(len(v)),3)

    earliest_date = min(date_sentiment.keys())

    print(earliest_date)
    print(date_sentiment)

    return (date_sentiment, earliest_date)

    