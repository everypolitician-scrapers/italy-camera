# -*- coding: utf-8 -*-
from datetime import datetime
import locale
import re
import time

from bs4 import BeautifulSoup as bs
import requests
import scraperwiki


locale.setlocale(locale.LC_ALL,'it_IT.utf8')

base_url = "http://www.camera.it"
url_tmpl = base_url + "/leg17/313?shadow_deputato_is_deputato_in_carica=1&current_page_2632={page}&shadow_deputato_has_sesso={gender}"

def fetch_member(url):
    print("Fetching: {}".format(url))
    r = requests.get(url)
    time.sleep(0.5)
    soup = bs(r.text, "html.parser")
    member = {}

    email_button = soup.find("div", {"class": "buttonMail"})
    if email_button:
        email = email_button.a["href"].split('=')[-1]
        member["email"] = email if '@' in email else None

    bio_soup = soup.find("div", {"class": "datibiografici"})
    if bio_soup:
        bio = bio_soup.text
        dob_str = "{} {} {}".format(*re.search(ur'(\d+)\xb0?\s+([^ ]+)\s+(\d{4})', bio).groups())
        member["birth_date"] = datetime.strptime(dob_str, "%d %B %Y").strftime("%Y-%m-%d")

    election_data_soup = soup.find("div", {"class": "datielettoriali"})
    if election_data_soup:
        election_data = election_data_soup.text
        member["area"] = re.search(r'\(([^\)]+)\)', election_data).groups()[0]
        party = re.search(r'Lista di elezione\s+(.*?)\n', election_data)
        if party:
            member["party"] = party.groups()[0]

    return member

def fetch_members(gender):
    page = 0
    while True:
        page += 1
        url = url_tmpl.format(page=page, gender=gender)
        print("Fetching: {}".format(url))
        r = requests.get(url)
        time.sleep(0.5)
        soup = bs(r.text, "html.parser")
        members_ul = soup.find("ul", {"class": "main_img_ul"})
        if not members_ul:
            break
        member_lis = members_ul.find_all("li")
        members = []
        for member_li in member_lis:
            url = base_url + "/leg17/" + member_li.a['href'].replace('\n', '')
            member = fetch_member(url)
            members.append({
                "id": member_li['id'][12:],
                "birth_date": member.get("birth_date"),
                "area": member.get("area"),
                "party": member.get("party"),
                "email": member.get("email"),
                "name": member_li.find("div", {"class": "nome_cognome_notorieta"}).text.strip(),
                "image": base_url + member_li.img['src'],
                "gender": "female" if gender == "F" else "male",
                "term": 17,
                "source": url,
            })
        scraperwiki.sqlite.save(["id"], members, "data")

for gender in ["F", "M"]:
    fetch_members(gender)
