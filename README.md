### STPH Scheldestromen

Deze repository bevat de scripts voor de STPH berekenening voor de Zak van Zuid-Beveland

### Environment variables

Voor de werking van het script moet er in de directory waar main.py staat een .env bestand gemaakt zijn met de volgende waardes;

* PATH_INPUT_FILES, het pad naar de invoerbestanden directory
* PATH_OUTPUT_FILES, het pad waar uitvoerbestanden geschreven kunnen worden
* TOETSING_PICKLE, de naam van het bestand met de relevante invoergegevens
* WBI_LOG_PICKLE, de naam van het bestand met alle invoergegevens

Een voorbeeld is;

```
PATH_INPUT_FILES="D:\Documents\Scheldestromen\uitgangspunten\python_20231107\data_prepoc"
PATH_OUTPUT_FILES="D:\Documents\_TEMP\ScheldeStromen"
TOETSING_PICKLE="wbi_log_toetsing_relevant.pkl"
WBI_LOG_PICKLE="wbi_log.pkl"
```