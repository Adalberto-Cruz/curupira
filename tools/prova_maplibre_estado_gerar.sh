#!/bin/sh
# Somente a prova adicional. Executar no WSL do usuário com binário já existente.
set -eu
: "${TIPPECANOE:?Informe o binário isolado do Tippecanoe 2.79.0}"
: "${PROVA_DIR:?Informe work/prova-maplibre em caminho Linux}"
: "${PROVA_UF:?Informe mt ou pa}"
case "$PROVA_UF" in mt|pa) ;; *) printf 'UF inválida\n' >&2; exit 1;; esac
test -f "$PROVA_DIR/car-$PROVA_UF.geojson"
test ! -e "$PROVA_DIR/car-$PROVA_UF.pmtiles"
BUILD_DIR=$(mktemp -d /tmp/hibama-maplibre-estado.XXXXXX)
cp "$PROVA_DIR/car-$PROVA_UF.geojson" "$BUILD_DIR/input.geojson"
"$TIPPECANOE" --version
"$TIPPECANOE" -o "$BUILD_DIR/output.pmtiles" -l car -Z4 -z14 \
 --full-detail=14 --simplify-only-low-zooms --drop-densest-as-needed \
 --no-tiny-polygon-reduction --simplification=2 --include=code --include=status \
 "$BUILD_DIR/input.geojson"
cp "$BUILD_DIR/output.pmtiles" "$PROVA_DIR/car-$PROVA_UF.pmtiles"
printf 'Estado gerado; intermediários preservados em %s\n' "$BUILD_DIR"
