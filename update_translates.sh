#!/bin/bash

TRANSLATE_FILES=`find ./src/ -iname "*.py" -o -iname "*.ui"`

#Create base file
#pylupdate4 -noobsolete ./src/*.{py,ui} -ts ./src/i18n/base.ts

#Update translate files
pylupdate5 -noobsolete $TRANSLATE_FILES -ts ./src/i18n/*.ts
echo "TS files have been updated!"

#Check
for file in `ls ./src/i18n/*.ts|grep -v base.ts`
do
str_to_update=`grep -c 'type="unfinished"' $file`
if [ $str_to_update -gt 0 ];
then
      echo "Need to retranslate: $file ($str_to_update string(s))"
fi
done
