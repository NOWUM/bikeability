# Anwendung
Im folgenden Abschnitt wird erläutert, wie mithilfe des entwickelten Modells und des bereitgestellten Programmcodes eine Bikeability-Bewertung durchgeführt werden kann. 

## Eingabedaten
Vor Durchführung der Bikeability-Berechnung ist eine Überprüfung der Eingabedaten notwendig. 
Diese sind in der beigefügten Datei "bikeability_config.py" zu finden. 

Der wichtigste Eingabewert ist dabei die Angabe der gewählten Stadt. Diese kann unter CITY im Format "[Stadt]/[Land]" angegeben werden. Sollte lokal auf dem Gerät bereits eine Protobuff-Datei zur betroffenen Stadt vorhanden sein, kann diese als "PBF_PATH" angegeben werden, ansonsten wird sie im Programmdurchlauf heruntergeladen. 

An dieser Stelle muss, mittels des Parameters "USE_ACCIDENTS", ebenfalls angegeben werden, ob Unfalldaten verwendet werden sollen. Dies ist für nicht deutsche Städte nur möglich, wenn unter "ACCIDENT\_PATH" eine h5-Datei abgelegt wird, die Unfalldaten für die gewählte Stadt enthält. 

## Profile
Wenn für die Bikeability-Berechnung ein vom Default abweichendes Nutzerprofil, mit einer individuellen Bewertung der Wichtigkeit von POIs verwendet werden soll, kann dieses ebenfalls in der config-Datei angegeben werden. Das Format ist dabei folgendermaßen zu verstehen:
POIs sind in 9 Kategorien unterteilt. Diese stehen jeweils symbolisch für eine Reihe an OSM-Tags, die im Programmdurchlauf der jeweiligen Kategorie zugeordnet werden.
Jede Kategorie kann Gewichtsfaktoren erhalten, die repräsentieren, mit welcher Priorität die nächste, zweitnächste, etc. Instanz eines POI der jeweiligen Kategorie in den Score Bikeability-Score von Wohngebäuden eingeht. Die Anzahl dieser Gewichtsfaktoren kann beliebig groß sein, wirkt sich aber direkt auf die Laufzeit des Programms aus. Die Zahlenwerte der Gewichte können dabei beliebig groß sein, da sie nur im Verhältnis zu anderen Gewichtsfaktoren derselben Tabelle betrachtet werden. Das heißt, dass die Erreichbarkeit eines POI mit einem Gewichtsfaktor von 8 den achtfachen Einfluss auf den Score von Gebäuden hat, wie ein POI mit einem Gewichtsfaktor von 1. 