#!/usr/bin/env python3

from pocket import Pocket, PocketException
import feedparser
import requests
from pprint import pprint


# def hn_pop():for url in articles:
# print("%s %s", url.resolved_title, url.resolved_url)
# pprint(url)
# Do a thing in here


def pocket_pop():
    conskey = "82886-5fc8d766c10eed195a362668"
    acctok = "0f2a6d6d-096a-8586-ded1-15cef6"

    p = Pocket(
        consumer_key=conskey,
        access_token=acctok
    )

    retstr = "\n### Articles I've added to my [GetPocket](https://getpocket.com/) list\n\n"

    try:
        articles = p.retrieve(offset=0, count=10)
        for url in articles['list'].values():
            # print("* [{}]({})\n".format(url['resolved_title'], url['resolved_url']))
            retstr += "* [{}]({})\n".format(url['resolved_title'], url['resolved_url'])
    except PocketException as e:
        print(e.message)

    return retstr


def pgmac_pop(l_url):
    retstr = "\n### My Blog Posts\n\n"
    try:
        articles = feedparser.parse(l_url)
        for article in articles['entries']:
            # print("{} {}".format(article['title'], article['link']))
            retstr += "* [{}]({})\n".format(article['title'], article['link'])
    except:
        pass

    return retstr


def github_stars(l_user="pgmac", max=10):
    # retarr = "\n### {}'s GitHub Stars".format(l_user)
    retarr = []
    r = requests.get("https://api.github.com/users/{}/starred".format(l_user))
    if r.status_code == 200:
        for idx, ghstar in enumerate(r.json()):
            if idx > max:
                break
            stararr = {}
            stararr['name'] = ghstar['name']
            stararr['url'] = ghstar['html_url']
            stararr['desc'] = ghstar['description']
            retarr.append(stararr)

    return retarr

def add_file(l_file):
    return open(l_file, "r").read()


def write_file(l_string, l_file):
    with open(l_file, "w") as f:
        f.write(l_string)
    f.close()


readme = ""
if __name__ == "__main__":
    readme = add_file("src/HEADER.md")
    readme += pocket_pop()
    readme += pgmac_pop('https://pgmac.net.au/feed.xml')
    readme += "\n### Things I'm star-ing\n\n"
    for star in github_stars('pgmac'):
        readme += "* [{}]({})\n  {}\n".format(star["name"], star["url"], star["desc"])
    readme += add_file("src/FOOTER.md")
    # print(readme)
    write_file(readme, "README.md")
