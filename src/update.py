#!/usr/bin/env python3

# from pocket import Pocket, PocketException
from os import environ
import feedparser
import requests


def links_pop():
    """Get the newest 10 links from my Link Ace
    ----------- Creates a string of HREF's to insert into README.md
    Returns:
        str: A formatted string of links
    """

    api_url = "https://links.pgmac.net.au/api/v2/links"
    headers = {
        'Authorization': f"Bearer {environ.get('PGLINKS_KEY')}",
        'accept': 'application/json'
    }
    params = {
        'per_page': 10,
        'order_by': 'created_at',
        'order_dir': 'desc'
    }
    try:
        response = requests.get(api_url, timeout=30, headers=headers, params=params)
        response.raise_for_status()
        for link in response.json().get('data', []):
            link_id = link.get('id')
            if not link_id:
                continue
            title = link.get('title', 'No Title')
            url = link.get('url', '#')
            yield f"* [{title}]({url})"
    except requests.RequestException as e:
        print(f"Error fetching links from API: {e}")
        return {}
    return {}


def pocket_pop():
    conskey = environ.get("POCKET_CONSKEY")
    acctok = environ.get("POCKET_ACCTOK")

    p = Pocket(
        consumer_key=conskey,
        access_token=acctok
    )

    retstr = "\n### Articles I've added to my [GetPocket](https://getpocket.com/) list\n\n"

    try:
        articles = p.retrieve(offset=0, count=10)
        for url in articles['list'].values():
            # print("* [{}]({})\n".format(url['resolved_title'], url['resolved_url']))
            retstr += "* [{}]({})\n".format(url.get('resolved_title', '&nbsp;'), url.get('resolved_url', '#'))
    except PocketException as e:
        print(e.message)

    return retstr


def pgmac_pop(l_url):
    retstr = "\n### My Blog Posts\n\n"
    try:
        articles = feedparser.parse(l_url)
        retstr += "* [{}]({})\n".format("Things I'm interested in Last Week", "https://pgmac.net.au/last-week/")
        for article in articles['entries']:
            found_last_week = any(item['term'] == 'Last-Week' for item in article['tags'])
            if found_last_week:
                continue
            else:
                retstr += "* [{}]({})\n".format(article['title'], article['link'])
    except:
        pass

    return retstr


def github_stars(l_user="pgmac", l_max=10):
    retarr = []
    r = requests.get("https://api.github.com/users/{}/starred".format(l_user))
    if r.status_code == 200:
        for idx, ghstar in enumerate(r.json()):
            if idx > l_max:
                break
            stararr = {}
            stararr['name'] = ghstar['name']
            stararr['url'] = ghstar['html_url']
            stararr['desc'] = ghstar['description']
            retarr.append(stararr)

    return retarr

def ghstars_pop(l_user="pgmac", l_max=10):
    retstr = "\n### Things I'm star-ing\n\n"
    for star in github_stars(l_user, l_max):
        retstr += "* [{}]({})\n  {}\n".format(star["name"], star["url"], star["desc"])

    return retstr

def add_file(l_file):
    return open(l_file, "r").read()


def write_file(l_string, l_file):
    with open(l_file, "w") as f:
        f.write(l_string)
    f.close()


readme = ""
if __name__ == "__main__":
    readme = add_file("src/HEADER.md")
    readme += '\n'.join([str(x) for x in links_pop()])
    # readme += pocket_pop()
    readme += ghstars_pop('pgmac')
    readme += pgmac_pop('https://pgmac.net.au/feed.xml')
    readme += add_file("src/FOOTER.md")
    write_file(readme, "README.md")
