### STPH Scheldestromen

Deze repository bevat de scripts voor de STPH berekenening voor de Zak van Zuid-Beveland

### Environment variabelen

Deze repository maakt gebruik van d-geolib waarbij het noodzakelijk is om DGeoFlow van Deltares geinstalleerd te hebben. Vervolgens dient in de root van deze directory een geolib.env bestand aangemaakt te worden met de verwijzing naar het pad naar de Deltares reken consoles. Voor meer informatie zie [deze website](https://deltares.github.io/GEOLib/latest/user/setup.html) 

### Settings

De instellingen vor het script zijn te vinden in het settings.py bestand. In dit bestand worden onder andere de locaties van de in- en uitvoerbestanden opgegeven en worden specifieke rekenparameters bepaald. De toelichting van de parameters staan in de commentaren in het script.

### Uitvoeren script

* Clone de repository naar een eigen map;

```git clone https://github.com/breinbaas/stph_scheldestromen.git```

* Maak een virtuele omgeving aan (venv)

```python -m venv .venv```

* Activeer de omgeving

```.venv/scripts/activate```

* Installeer de afhankelijkheden

```python -m pip install -r requirements.txt```

Het script kan eenvoudig uitgevoerd worden door het main.py bestand te activeren via ```python main.py```. Afhankelijk van de hoeveelheid invoergegevens en met name dit dichtheid van de grids kunnen de berekeningen lang duren. 

### Mogelijke bugs / problemen

Op dit moment (februari 2024) is de nieuwste versie van pydantic niet compatible met de laatste versie van d-geolib. Mochten er problemen optreden dan kan dit worden opgelost door 

```pydantic==1.10.14``` in het requirements bestand op te nemen.

Let wel, er wordt aan d-geolib gewerkt om de nieuwste versie van pydantic te ondersteunen.


### Code, git branches en historie

In de code is door middel van comments / docstrings zo goed mogelijk aangegeven wat de code doet en waar deze voor dient. De commentaren zijn -als een typische programmeur- deels in het Nederlands en in Engels.

In de loop van het project zijn veel aanpassingen geweest die door voortschrijdend inzicht noodzakelijk waren. Alle oude code is terug te vinden in de git history in de repository. 

De branches volgens het git flow principe waarbij het ontwikkelwerk in feature branches worden uitgewerkt, de goedgekeurde feature code naar de develop tak gaat en na goedkeuring naar de main tak gaat. 

Voor dit project staat er momenteel (februari 2024) 1 feature tak open die speciaal geopend is voor een specifieke vraag (dikte afdeklaag). Dit betreft tijdelijke code die eventueel nog ingezet kan worden als het nodig mocht zijn maar nooit naar de develop of main branch gepushed zal worden.

Bij de oplevering zijn de develop en main branch hetzelfde.

### Ontwikkelaar tips

* gebruik black voor automatische code formatting
* gebruik git flow voor overzichtelijk versiebeheer

