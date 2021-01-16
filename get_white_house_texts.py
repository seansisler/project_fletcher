from bs4 import BeautifulSoup as bs
import requests
from datetime import datetime as dt
from datetime import timedelta
import numpy as np
import pandas as pd 
import re
import time
import unicodedata


def get_data_whpb():
    
    whitehouse_briefings, briefing_retry = get_press_briefings_links(tab='briefings')
    whitehouse_briefings['clean_briefings'] = whitehouse_briefings['soup'].map(get_html_clean)
    whitehouse_briefings.reset_index(drop=True, inplace=True)
    briefings = expand_df(whitehouse_briefings, remarks_or_briefings='briefings')
    briefings.to_csv('briefings-for-cleaning.csv', index=False)
    print('Briefing complete')
    
    whitehouse_remarks, remark_retry = get_press_briefings_links(tab='remarks')
    whitehouse_remarks['clean_remarks'] = whitehouse_remarks['soup'].map(get_html_clean)
    whitehouse_remarks.reset_index(drop=True, inplace=True)
    remarks = expand_df(whitehouse_remarks, remarks_or_briefings='remarks')
    remarks.to_csv('remarks-for-cleaning.csv', index=False)
    print('Briefings and remarks complete')
    
    return_dictionary = {'from remarks': remark_retry, 
                         'from briefing': briefing_retry, 
                         'original_remarks': whitehouse_remarks, 
                         'original_briefings':whitehouse_briefings}
    
    return remarks, briefings, return_dictionary


def drop_blank_text(df):
    df['text'] = df['text'].replace('', np.nan)
    df = df.dropna(subset=['text'])
    return df.reset_index(drop=True)

def clean_html_leftovers(column):
    column = column.apply(lambda x: unicode.normalize("NFKD", x))
    return column.str.replace('\\n', regex=False)

def get_press_briefings_links(tab, start_date=dt.now().date(), stop=1500):
    ending = 'The Inaugural Address'
    df = pd.DataFrame(columns=['title', 'date', 'soup', 'link'])
    retry_indiv_pages = []
    retry_pages = []
    end = stop
    for num in range(1, end):
        if tab == 'briefings':
            page = get_webpage(url=f'https://www.whitehouse.gov/briefings-statements/page/{num}/')
        if tab == 'remarks':
            page = get_webpage(url=f'https://www.whitehouse.gov/remarks/page/{num}/')
        if type(page) is int:
            if page == 404:
                break
            else:
                retry_pages.append(url)
                continue
        sep_pages = get_individual_links(page)
        temp_df, indiv_retry = make_compliation_soup(sep_pages)
        if len(indiv_retry) > 0:
            retry_indiv_pages += indvi_retry
        df = pd.concat([df, temp_df])
        if df.iloc[-1]['title'] == 'The Inaugural Address':
            break
    retry_dictionary = {'individual pages': retry_indiv_pages, 'result pages': retry_pages}
    return df, retry_dictionary
        
        
def get_webpage(url):   
    response = requests.get(url)
    if response.status_code != 200:
        time.sleep(15)
        return response.status_code
    return bs(response.text, 'html.parser')

def get_individual_links(soup):
    individual_pages = []
    for article in soup.find_all('article', class_='briefing-statement briefing-statement--results'):
        content = article.find('a', href=True)
        date = article.find('time').text
        link = content['href']
        title = content.text
        individual_pages.append([link, title, date])
    return individual_pages

def make_compliation_soup(pages):
    temp = []
    retry = []
    for page in pages:
        link = page[0]
        soup = get_webpage(link)
        if not soup:
            retry.append(page)
            continue
        temp.append([page[1], page[2], soup, link])
    return pd.DataFrame(temp, columns=['title', 'date', 'soup', 'link']), retry

def get_html_clean(soup):
    return [tag.text.strip() for tag in soup.find_all('p')]

def drop_blank_text(df):
    df['text'] = df['text'].apply(lambda x: unicodedata.normalize("NFKD", x))
    df['text'] = df['text'].replace('\\n', ' ', regex=False)
    df['text'] = df['text'].str.strip()
    df['text'] = df['text'].replace('', np.nan)
    df = df.dropna(subset=['text'])
    return df.reset_index(drop=True)


def expand_row(row, remarks_or_briefings):
    if remarks_or_briefings == 'remarks':
        return [[row['title'], row['date'], text, row['link'], row.name] for text in row['clean_remarks']]
    if remarks_or_briefings == 'briefings':
        return [[row['title'], row['date'], text, row['link'], row.name] for text in row['clean_briefings']]
                 
def expand_df(df, remarks_or_briefings):
    df = pd.DataFrame([x for i in df.apply(lambda x: expand_row(row=x, 
                                                                  remarks_or_briefings=remarks_or_briefings), 
                                             axis=1).tolist() for x in i], columns=['title', 'date', 'text', 'link', 'doc_id'])
    df = drop_blank_text(df)
    df['date'] = pd.to_datetime(df['date'])
    return df