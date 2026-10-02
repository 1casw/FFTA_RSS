"""Flux RSS des résultats de compétitions FFTA (filtre dep=58 de l’adresse, 12 mois glissants)."""

import sys
from datetime import date, timedelta
from xml.etree.ElementTree import Element, ElementTree, SubElement

from ffta_site import absolute_url, competitions_url, fetch_competition_articles, text_of

OUTPUT_FILE = "FFTA_Resultats_Competitions.xml"

end_date = date.today()
start_date = end_date - timedelta(days=365)
url = competitions_url(start_date, end_date, sort_order="DESC")

print("URL FFTA utilisée :")
print(url)
print()


# --- Lecture des compétitions -------------------------------------------------
# Le titre et le lien « Résultats » sont lus dans le MÊME bloc <article> : une
# compétition sans bouton de résultats est simplement ignorée, sans décaler les autres.

competitions = []
articles = fetch_competition_articles(url)

for article in articles:
    title = text_of(article, ".competition_item__title")
    button = article.select_one("a.competition_item__results_btn")
    link = absolute_url(button.get("href", "")) if button else ""

    if title and link:
        competitions.append({"title": title, "link": link})

print()
print("Compétitions avec titre + lien :", len(competitions), "sur", len(articles))

if not competitions:
    print()
    print("ERREUR : aucune compétition exploitable.")
    print("Le RSS ne sera pas remplacé.")
    sys.exit(1)

print()
print("Compétitions qui seront placées dans le RSS :")
print()
for competition in competitions:
    print("-", competition["title"])
    print("  ", competition["link"])


# --- Création du RSS ----------------------------------------------------------

rss = Element("rss", {"version": "2.0"})
channel = SubElement(rss, "channel")

SubElement(channel, "title").text = "FFTA - Résultats des compétitions"
SubElement(channel, "description").text = (
    "Résultats des compétitions FFTA pour le département 57."
)
SubElement(channel, "link").text = "https://www.ffta.fr/competitions"
SubElement(channel, "language").text = "fr"

for competition in competitions:
    item = SubElement(channel, "item")
    SubElement(item, "title").text = competition["title"]
    SubElement(item, "link").text = competition["link"]
    SubElement(item, "guid").text = competition["link"]
    SubElement(item, "description").text = f"Résultats : {competition['title']}"

ElementTree(rss).write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)

print()
print("========================================")
print("RSS généré avec succès !")
print("========================================")
print()
print("Fichier créé :", OUTPUT_FILE)
print(f"Période FFTA : {start_date.isoformat()} → {end_date.isoformat()}")
