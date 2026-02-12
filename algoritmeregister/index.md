---
layout: default
title: Algoritmeregister Wijzigingen
nav_order: 5
has_children: true
---

# Algoritmeregister Wijzigingen

Deze pagina toont wijzigingen in het [Algoritmeregister van de Nederlandse overheid](https://algoritmes.overheid.nl/nl).

Het Algoritmeregister wordt periodiek gecontroleerd op nieuwe, gewijzigde en verwijderde algoritme-registraties.

## Over deze tracker

De tracker controleert dagelijks het [Algoritmeregister](https://algoritmes.overheid.nl/nl) op wijzigingen. Dit omvat:

- **Nieuwe registraties** - algoritmes die voor het eerst in het register verschijnen
- **Gewijzigde registraties** - bestaande algoritmes waarvan de gegevens zijn aangepast
- **Verwijderde registraties** - algoritmes die uit het register zijn verwijderd

### Hoe werkt het?

1. Dagelijks wordt een snapshot van alle algoritme-registraties opgehaald via de [openbare API](https://algoritmes.overheid.nl/api/downloads/site-data/json)
2. De huidige snapshot wordt vergeleken met de vorige
3. Verschillen worden vastgelegd en hier gepubliceerd

### Gevolgde velden

De volgende velden worden gemonitord op wijzigingen:

| Veld | Beschrijving |
|---|---|
| name | Naam van het algoritme |
| description_short | Korte beschrijving |
| organization | Verantwoordelijke organisatie |
| status | Status (In ontwikkeling / In gebruik / Buiten gebruik) |
| publication_category | Categorie (A, B, of C) |
| purpose_and_impact | Doel en impact |
| considerations | Afwegingen |
| human_intervention | Menselijke tussenkomst |
| risk_management | Risicobeheer |
| legal_basis | Wettelijke grondslag |
| data | Gebruikte data |
| technical_operation | Technische werking |
| supplier | Leverancier |
| contact | Contactgegevens |
| theme | Beleidsterrein |
| start_date | Startdatum |
| end_date | Einddatum |

### Broncode

De broncode van de tracker is beschikbaar in de [`tracker/`](https://github.com/j3vh/aicompdocs/tree/main/tracker) map van deze repository.
