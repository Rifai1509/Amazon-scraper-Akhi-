import glob
import json
import os
import requests
from bs4 import BeautifulSoup

session = requests.Session()

with open('./params.json', encoding="utf-8") as json_file:
    data = json.load(json_file)

cookie = data['cookie']

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'max-age=0',
    # 'cookie': cookie,
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36',
}

if cookie != '':
    headers['cookie']: cookie


def get_location_sessions(zip):
    location_url = 'https://www.amazon.com/gp/delivery/ajax/address-change.html'
    data = {
        'locationType': 'LOCATION_INPUT',
        'zipCode': zip,
        'storeContext': 'merchant-items',
        'deviceType': 'web',
        'pageType': 'Search',
        'actionSource': 'glow',
        'almBrandId': 'undefined',
    }
    session.post(location_url, headers=headers, data=data)

    return session


def get_page_total(url):
    res = session.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html5lib')
    total_pages = soup.find_all('li', attrs={'class': 'a-disabled'})
    total_pages = int(total_pages[-1].text)

    return total_pages


def get_links_per_page(page_total, url_):
    for page in range(page_total):
        page += 1
        print('getting links from page {} of {}'.format(page, page_total))
        url = '{}&page={}'.format(url_, page)
        res = session.get(url, headers=headers)

        soup = BeautifulSoup(res.text, 'html5lib')
        h2_title = soup.find_all('h2', attrs={'class': 's-line-clamp-2'})

        links = []
        for title in h2_title:
            link = title.find('a')['href']
            links.append('https://www.amazon.com' + link)

        with open('./json-links-per-page/{}.json'.format(page), 'w', encoding="utf-8") as outfile:
            json.dump(links, outfile)



if __name__ == '__main__':
    with open('./params.json', encoding="utf-8") as json_file:
        data = json.load(json_file)

    zip = data['zip']
    url = data['url']

    get_location_sessions(zip)
    page_total = get_page_total(url)
    print(page_total)

    files = glob.glob('./json-links-per-page/*')
    for f in files:
        os.remove(f)

    get_links_per_page(page_total, url)