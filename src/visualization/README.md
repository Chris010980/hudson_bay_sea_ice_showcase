# GeoTIFF-Visualisierung für Sea-Ice-Plots

Diese Visualisierung erwartet ein GeoTIFF mit räumlich referenzierten Konzentrationswerten und erzeugt daraus eine regionale Karte für die Hudson Bay.

## Daten-Transformation

1. Das GeoTIFF wird über Pillow und tifffile geladen.
2. Falls die Seite ein 3D-Array enthält, wird die erste Bandebene verwendet.
3. Die Georeferenzierung wird aus den Tags `ModelPixelScaleTag` und `ModelTiepointTag` abgeleitet.
4. Die Pixelkoordinaten werden aus dem Quell-CRS `EPSG:3411` nach `EPSG:4326` transformiert.
5. Längengrade werden auf das Format `0..360` normalisiert.
6. Das TIFF wird als palettierte Bilddatei behandelt und mit der eingebetteten Farbtabelle dargestellt; es wird nicht künstlich als Konzentrationswertskala interpretiert.
7. Ungültige oder fehlende Pixel bleiben transparent bzw. werden nicht als numerische Konzentrationswerte interpretiert.
8. Die Daten werden auf die gewünschte Region zugeschnitten und im Plot dargestellt.

## Erwartete Meta-Daten im TIFF

Die Plot-Logik geht von GeoTIFFs mit folgenden Eigenschaften aus:

- 2D-Raster (Höhe x Breite) oder 3D-Raster mit einem ersten Band
- `ModelPixelScaleTag` mit Pixelgröße in X/Y Richtung
- `ModelTiepointTag` mit einem Tie-Point, der die Raster-zu-Welt-Transformation beschreibt
- Ein räumlich referenziertes Raster im Polar- oder Projektionssystem, das in `EPSG:3411` beschrieben ist

Beispielhaft sieht die Annahme in etwa so aus:

- `ModelPixelScaleTag`: `(pixel_width, pixel_height, 0)`
- `ModelTiepointTag`: `(0, 0, 0, x_origin, y_origin, 0)`

Wenn diese Tags fehlen, fällt die Pipeline auf einen einfachen Fallback mit synthetischen Koordinaten zurück.

## Plot-Aussehen

Der Plot verwendet eine Nord-Polar-Stereoprojizierung und zeichnet einen leicht gekrümmten Rahmen rund um die betrachtete Region. Die Farbskala läuft von `0.0` (kein Eis / Meerfarbe) bis `1.0` (vollständig bedeckt).
