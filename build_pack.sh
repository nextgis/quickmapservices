#!/bin/bash

#Build zip packet
BUILD_DIR=/tmp/build_plugin
PLUGIN_NAME=quick_map_services

#Create if need
mkdir $BUILD_DIR

#Clear build dir
rm -R $BUILD_DIR/$PLUGIN_NAME
rm $BUILD_DIR/$PLUGIN_NAME*.zip

#Create plugin dir
mkdir $BUILD_DIR/$PLUGIN_NAME
#Copy sources
cp -R ./src/* $BUILD_DIR/$PLUGIN_NAME

#Clean
find $BUILD_DIR/$PLUGIN_NAME -name "*.pyc" -type f -delete
find $BUILD_DIR/$PLUGIN_NAME -name "*.pyo" -type f -delete
find $BUILD_DIR/$PLUGIN_NAME -name ".git" -type f -delete
find $BUILD_DIR/$PLUGIN_NAME -name ".gitignore" -type f -delete



#Remove Contrib
rm -R $BUILD_DIR/$PLUGIN_NAME/data_sources_contrib
rm -R $BUILD_DIR/$PLUGIN_NAME/groups_contrib

#Get version
cd $BUILD_DIR
VER=`grep "version=" ./$PLUGIN_NAME/metadata.txt | sed 's/version=//'`

# Compile resources
pyrcc4 -o ./$PLUGIN_NAME/resources_rc.py ./$PLUGIN_NAME/resources.qrc

#Zip dir
#zip -9 -r $PLUGIN_NAME"_"$VER.zip ./$PLUGIN_NAME
zip -9 -r $PLUGIN_NAME.zip ./$PLUGIN_NAME

#echo "Pack for upload: $BUILD_DIR/$PLUGIN_NAME"_"$VER.zip"
echo "Pack for upload: $BUILD_DIR/$PLUGIN_NAME.zip"