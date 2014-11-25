#!/bin/bash
LOCALES=$*

for LOCALE in ${LOCALES}
do
    echo "safe_qgis/i18n/inasafe_"${LOCALE}".ts"
    # Note we don't use pylupdate with qt .pro file approach as it is flakey
    # about what is made available.
    lrelease-qt4 ../src/i18n/${LOCALE}.ts
done
