import backoff
import glob
import json
import os
import re
import requests
import time
from bs4 import BeautifulSoup

session = requests.Session()

with open('./params.json', encoding="utf-8") as json_file:
    data = json.load(json_file)

cookie = data['cookie']
zip = data['zip']

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'max-age=0',
    # 'cookie': cookie,
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36',
}

if cookie != '':
    headers['cookie']: cookie


# Re-usable decorator with exponential wait.
retry_timeout = backoff.on_exception(
    wait_gen=backoff.expo,
    exception=(
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
    ),
    max_tries=3,
)


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

@retry_timeout
def get_detail():
    files = sorted(glob.glob('./json-links-per-page/*.json'), key=lambda x: float(re.findall("(\d+)", x)[0]))
    all_products_url = []
    for f in files:
        with open(f, encoding="utf-8") as json_file:
            data = json.load(json_file)
        all_products_url += data

    print('Total products: {}'.format(len(all_products_url)))
    start = int(input('Input product index start: '))
    end = int(input('Input product index end: '))
    product_url_selected = all_products_url[start-1:end]

    for url in product_url_selected:
        session.close()
        start += 1
        index_position = start-1
        print('getting product : {}'.format(index_position))
        print(url)
        res = session.get(url, headers=headers)
        if 'Robot Check' in res.text:
            raise Exception('BLOCKED BY RECAPTCHA. Open browser and refresh cookie..')

        f = open('temp.html', 'w+', encoding="utf-8")
        f.write(res.text)
        f.close()

        soup = BeautifulSoup(res.text, 'html5lib')

        table1 = soup.find('table', attrs={'id': 'productDetails_detailBullets_sections1'})
        feature_area = soup.find('div', attrs={'id': 'feature-bullets'})

        data_dict = {
            'ASIN': '',
            'TITLE': '',
            'PRICE': '',
            'FEATURE 1': '',
            'FEATURE 2': '',
            'FEATURE 3': '',
            'FEATURE 4': '',
            'FEATURE 5': '',
            'PRODUCT DESCRIPTION': '',
            'BEST SELLER RANK': '',
            'ALL PHOTO URL': ''
        }

        try:
            description = ' '.join(soup.find('div', attrs={'id': 'productDescription'}).text.replace('\n', '').split())
        except AttributeError:
            description = ''

        data_dict['PRODUCT DESCRIPTION'] = description

        if table1 is not None:
            table_row = table1.find_all('tr')
            for row in table_row:
                if 'ASIN' in str(row):
                    data_dict['ASIN'] = row.find('td').text.strip()
                if 'Best Sellers Rank' in str(row):
                    spans = row.find('span').find_all('span')
                    best_seller = []
                    for span in spans:
                        best_seller.append(span.text.strip().split('(')[0])
                    data_dict['BEST SELLER RANK'] = '\n'.join(best_seller)
        else:
            tables = soup.find_all('table')
            for table in tables:
                if 'Product details' in str(table):
                    table_row = table
                    lists_li = table_row.find_all('li')
                    for item_list in lists_li:
                        if 'ASIN' in str(item_list):
                            data_dict['ASIN'] = item_list.text.strip().replace('ASIN: ', '')

                    try:
                        rank = table_row.find('li', attrs={'id': 'SalesRank'}).text.strip()
                        all_rank = rank.replace('\n', '').replace('Amazon Best Sellers Rank: ', '').split('#')
                        ranks = []
                        for rank in all_rank:
                            if rank == '':
                                continue
                            rank = rank.split('(')[0]
                            rank = ' '.join(rank.split())
                            ranks.append('#'+rank)
                        data_dict['BEST SELLER RANK'] = '\n'.join(ranks)
                    except AttributeError:
                        data_dict['BEST SELLER RANK'] = ''
                else:
                    table_row = table.find_all('tr')
                    for row in table_row:
                        td = row.find_all('td')
                        for td_ in td:
                            if 'ASIN' in str(str(td_)):
                                data_dict['ASIN'] = td[1].text.strip()
                            if 'Best Sellers Rank' in str(str(td_)):
                                all_rank = td[1].text.strip().replace('\n', '').split('#')
                                ranks = []
                                for rank in all_rank:
                                    if rank == '':
                                        continue
                                    rank = rank.split('(')[0]
                                    rank = ' '.join(rank.split())
                                    ranks.append('#' + rank)
                                data_dict['BEST SELLER RANK'] = '\n'.join(ranks)

        title = soup.find('h1', attrs={'id': 'title'}).text.strip()
        data_dict['TITLE'] = title

        if 'Currently unavailable' in soup.text:
            price = 'Currently unavailable'
        else:
            price_ = soup.find('span', attrs={'id': 'priceblock_ourprice'})
            price = price_.text.strip()

        data_dict['PRICE'] = price

        try:
            list_item = feature_area.find_all('span', attrs={'class': 'a-list-item'})
            list_item = list_item[1:]
            features = []
            for item in list_item:
                features.append(item.text.strip())

            for idx, feature in enumerate(features):
                data_dict['FEATURE {}'.format(idx+1)] = feature

        except AttributeError:
            try:
                feature_area = soup.find('div', attrs={'id': 'feature-bullets-btf'})
                list_item = feature_area.find_all('li')
                features = []
                for item in list_item:
                    features.append(item.text.strip())
                for idx, feature in enumerate(features):
                    data_dict['FEATURE {}'.format(idx + 1)] = feature
            except AttributeError:
                pass

        imgs = []
        js = soup.find_all('script')
        for script in js:
            if 'ImageBlockATF' in script.text:
                script_text = script.text.replace('\n', '').replace(' ', '')
                script_text = script_text.split("{'colorImages':")[1].split(",'colorToAsin'")[0]
                selected_script = json.loads(script_text.replace("'", "\""))
                initial = selected_script['initial']

                for item in initial:
                    if item['hiRes'] is None:
                        imgs.append(item['large'])
                    else:
                        imgs.append(item['hiRes'])

        imgs = ', '.join(imgs)
        data_dict['ALL PHOTO URL'] = imgs

        with open('./details/{}.json'.format(index_position), 'w', encoding="utf-8") as outfile:
            json.dump(data_dict, outfile)

        # session.close()
        # time.sleep(2)


if __name__ == '__main__':
    get_location_sessions(zip)
    get_detail()
    # os.remove('./temp.html')
