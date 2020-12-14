#!/usr/bin/env python

from pocket import Pocket, PocketException
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

    try:
        articles = p.retrieve(offset=0, count=10)
        for url in articles['list'].values():
            print("{}\n{}\n".format(url['resolved_title'], url['resolved_url']))
    except PocketException as e:
        print(e.message)


def add_file(l_file):
    print(open(l_file, "r").read())


if __name__ == "__main__":
    add_file("src/HEADER.md")
    pocket_pop()
    add_file("src/FOOTER.md")
