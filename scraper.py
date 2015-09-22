# -*- coding: utf-8 -*-
from datetime import datetime
import locale
import re
import time

from bs4 import BeautifulSoup as bs
import requests
import scraperwiki


locale.setlocale(locale.LC_ALL,'it_IT.utf8')

term = "17"
base_url = "http://www.camera.it"
url_tmpl = base_url + "/leg17/313?current_page_2632={page}&shadow_deputato_has_sesso={gender}"

def parse_date(text):
    date = "{} {} {}".format(*re.search(ur'(\d+)\xb0?\s+([^ ]+)\s+(\d{4})', text).groups())
    return datetime.strptime(date, "%d %B %Y").strftime("%Y-%m-%d")

def fetch_member(url):
    print("Fetching: {}".format(url))
    r = requests.get(url)
    time.sleep(0.5)
    soup = bs(r.text, "html.parser")
    member = {}

    if soup.find("span", {"class": "external_source_error"}):
        return member

    name = soup.find("div", {"class": "nominativo"}).text
    party_id_match = re.search(r"\s+-\s+(.*)", name)
    if party_id_match:
        member["party_id"] = party_id_match.group(1)

    email_button = soup.find("div", {"class": "buttonMail"})
    if email_button:
        email = email_button.a["href"].split('=')[-1]
        member["email"] = email if '@' in email else None

    bio_soup = soup.find("div", {"class": "datibiografici"})
    if bio_soup:
        member["birth_date"] = parse_date(bio_soup.text)

    election_data_soup = soup.find("div", {"class": "datielettoriali"})
    if election_data_soup:
        section_titles = election_data_soup.find_all('h4')

        for section_title in section_titles:
            title_text = section_title.text.strip()
            content_text = unicode(section_title.next_sibling)
            if title_text == "Eletto nella circoscrizione":
                area = content_text
                member["area_id"], member["area"] = re.search(r'([^\s]+) \(([^\)]+)\)', area).groups()
            elif title_text == "Lista di elezione":
                member["party"] = content_text
            elif title_text.startswith("Proclamat"):
                start_date = parse_date(content_text)
                if start_date > "2013-03-15":
                    member["start_date"] = start_date

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
            end_date = member_li.find("div", {"class": "has_data_cessazione_mandato_parlamentare"})
            if end_date:
                end_date = re.search(r'\d{2}\.\d{2}\.\d{4}', end_date.text).group()
                end_date = "{}-{}-{}".format(end_date[6:], end_date[3:5], end_date[:2])
            url = base_url + "/leg17/" + member_li.a['href'].replace('\n', '')
            if url[-1] == "=":
                url += term
            member = fetch_member(url)
            members.append({
                "id": member_li['id'][12:],
                "birth_date": member.get("birth_date"),
                "area_id": member.get("area_id"),
                "area": member.get("area"),
                "start_date": member.get("start_date"),
                "end_date": end_date,
                "party_id": member.get("party_id"),
                "party": member.get("party"),
                "email": member.get("email"),
                "name": member_li.find("div", {"class": "nome_cognome_notorieta"}).text.strip(),
                "image": base_url + member_li.img['src'],
                "gender": "female" if gender == "F" else "male",
                "term": term,
                "source": url,
            })
        scraperwiki.sqlite.save(["id"], members, "data")

for gender in ["F", "M"]:
    fetch_members(gender)
