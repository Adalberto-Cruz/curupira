#!/bin/sh
# Executar no Ubuntu existente. Não instala ferramentas nem usa sudo/apt.
set -eu
: "${TIPPECANOE:?Informe o caminho do Tippecanoe 2.79.0 isolado}"
: "${PROVA_DIR:?Informe work/prova-pmtiles em caminho Linux}"
# SQLite intermediário no filesystem Linux evita I/O lento no /mnt/c.
BUILD_DIR=$(mktemp -d /tmp/hibama-pmtiles-dados.XXXXXX)
cp "$PROVA_DIR/car-am.geojson" "$BUILD_DIR/car-am.geojson"
"$TIPPECANOE" --version
"$TIPPECANOE" -o "$BUILD_DIR/car-am.pmtiles" -l car -Z4 -z14 \
 --full-detail=14 --simplify-only-low-zooms --drop-densest-as-needed \
 --no-tiny-polygon-reduction --simplification=2 --include=code --include=status \
 "$BUILD_DIR/car-am.geojson"
cp "$BUILD_DIR/car-am.pmtiles" "$PROVA_DIR/car-am.pmtiles"
printf 'Arquivo gerado. Intermediários da prova preservados em %s\n' "$BUILD_DIR"
