"""Flux RSS des compétitions FFTA à venir (filtre dep=58 de l’adresse, 12 mois)."""

import sys
from datetime import date, timedelta
from html import unescape
from xml.etree.ElementTree import Element, ElementTree, SubElement

from ffta_site import competitions_url, fetch_competition_articles, link_with_text, text_of

OUTPUT_FILE = "FFTA_Competitions_a_Venir.xml"

start_date = date.today()
end_date = start_date + timedelta(days=365)
url = competitions_url(start_date, end_date, sort_order="ASC")

print("URL FFTA utilisée :")
print(url)
print()


# --- Lecture des compétitions -------------------------------------------------

competitions = []

for article in fetch_competition_articles(url):
    title = text_of(article, ".competition_item__title")
    detail = link_with_text(article, "Détail")

    # Une compétition sans titre ou sans lien Détail n'est pas ajoutée au RSS.
    if not title or not detail:
        continue

    competitions.append(
        {
            "title": unescape(title),
            "date": text_of(article, ".competition_item__dates"),
            "detail": detail,
            "mandat": link_with_text(article, "Mandat"),
        }
    )

print()
print("Compétitions exploitables :", len(competitions))
print("Mandats disponibles :", sum(1 for c in competitions if c["mandat"]))
print()

if not competitions:
    print("ERREUR : aucune compétition exploitable.")
    print("Le RSS ne sera pas remplacé.")
    sys.exit(1)

print("Compétitions qui seront placées dans le RSS :")
print()
for competition in competitions:
    print("-", competition["title"])
    print("  Date :", competition["date"] or "non disponible")
    print("  Détail :", competition["detail"])
    print("  Mandat :", competition["mandat"] or "non disponible")
    print()


# --- Création du RSS ----------------------------------------------------------

rss = Element("rss", {"version": "2.0"})
channel = SubElement(rss, "channel")

SubElement(channel, "title").text = "FFTA - Compétitions à venir"
SubElement(channel, "description").text = (
    "Calendrier des compétitions FFTA à venir pour le département 57."
)
SubElement(channel, "link").text = "https://www.ffta.fr/competitions"
SubElement(channel, "language").text = "fr"

for competition in competitions:
    item = SubElement(channel, "item")
    SubElement(item, "title").text = competition["title"]
    SubElement(item, "link").text = competition["detail"]
    SubElement(item, "guid").text = competition["detail"]

    if competition["date"] and competition["mandat"]:
        description = competition["date"] + "<br>  Mandat Disponible !"
    elif competition["date"]:
        description = competition["date"]
    elif competition["mandat"]:
        description = "Mandat Disponible !"
    else:
        description = ""
    SubElement(item, "description").text = description

ElementTree(rss).write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)

print("========================================")
print("RSS généré avec succès !")
print("========================================")
print()
print("Fichier créé :", OUTPUT_FILE)
print(f"Période FFTA : {start_date.isoformat()} → {end_date.isoformat()}")
print("Description : date de compétition + 'Mandat Disponible !' si un mandat existe.")
