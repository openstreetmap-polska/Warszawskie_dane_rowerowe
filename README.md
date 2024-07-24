# Warszawskie_dane_rowerowe
Dane infrastruktury rowerowej miasta Warszawa udostępnione dla edytorów OSM. Przekazane przez Warszawski ZDM

Skrócony opis pliku:
- rowery to infrastruktura rowerowa CPR/DDR/kontraruch itd.
- rowery towerowe (literówka) to punkty, gdzie można bezpłatnie wynająć rowery towarowe: https://warszawa19115.pl/-/rowery-towarowe
- stacje napraw to punkty, gdzie można proste naprawy samodzielnie wykonać: słupek z zestawem narzędzi i pompką, 

Dane będą aktualizowane poprzez nadpisanie.
Licencja zgodna z ODbL


Zmiany i wersje:
- Aktualizacja z dnia 11.10.2021
    - Dodano gotowe trasy i linie nowe będące obecnie w budowie oraz drobne poprawki, pełna lista zmian w pliku *aktualizacja.md*
- Aktualizacja z dnia 07.01.2022
    - Dodano gotowe trasy i linie nowe będące obecnie w budowie oraz drobne poprawki, pełna lista zmian w pliku *aktualizacja.md*
- Aktualizacja z dnia 22.08.2022
    - Aktualizacja zgodnie z najnowszymi danymi
- Aktualizacja z dnia 14.11.2022
    - Aktualizacja zgodnie z najnowszymi danymi
- Aktualizacja z dnia 03.01.2024
    - Stan na koniec grudnia 2023
- Aktualizacja z dnia 18.04.2024
  - Stan na marzec 2024
- Aktualizacja z dnia 22.07.2024

W pliku latestDiff.geojson znajduje się infrastruktura zmodyfikowana od ostatniej aktualizacji.

## Porównanie danych z OpenStreetMap
W folderze [osm_diffs](https://github.com/openstreetmap-polska/Warszawskie_dane_rowerowe/tree/main/osm_diffs) można znaleźć pliki w formacie GeoJSON.
Nazwy plików odpowiadają dzielnicom Warszawy lub podwarszawskim miejscowościom.
Są one automatycznie wygenerowane.
W każdym z nich znajduje się infrastruktura rowerowa z pliku rowery_wawa/rowery.shp, której nie udało się dopasować do infrastruktury w OpenStreetMap.
Czyli potencjalne braki do zmapowania w OSM.
Część różnic wynika z różnic w sposobie mapowania.

### Algorytm porównywania infrastruktury
1. Linie są zamieniane na [obszary H3](https://h3geo.org/) przez które przechodzą. Dla OSM z buforem.
2. Aktualnie porównuje się zbiory obszarów - nie bierze się pod uwagę typu infrastruktury. Czyli ulica, na której był pas rowerowy i została zbudowana DDR nie zostanie wykryta.
3. Dla każdej linii w danych miejskich sprawdza się ile obszarów nie da się odnaleźć
4. Uznaje się za brakującą linię jeżeli nie uda się odnaleźć 10 obszarów lub 20% wszystkich.

