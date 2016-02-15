# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import shutil
import pprint
import zipfile

skript_dir = os.path.dirname(sys.argv[0])

args = sys.argv[1:]
plugin_name = args[0]
plugin_dir = args[1]
targets = args[2:]

print "targets: ", targets

"""
Configuration
"""
BUILD_UI_FOR_TATGET_BUILD = False
IGNORE_PATTERNS_FOR_TARGET_INSTALL = (
    '*.pyc', '*.ts', '*.qrc', '.git'
    #'*.ui',
)

qgis_root = os.getenv("QGIS_BASE_DIR", None)
if qgis_root is None:
    sys.exit("QGIS_BASE_DIR env var not found!")
QGIS_PLUGINS_DIST_DIR = os.path.join(qgis_root, "apps", "qgis", "python", "plugins")

# TS_FILE_NAME = "%s_ru.ts" % plugin_name
TS_FILE_NAME = "QuickMapServices_ru.ts"

"""
Work section:
"""
def process_ui():
    print "process ui ..."
    
    ui_dir = os.path.join(plugin_dir, "src", "ui")
    if not os.path.exists(ui_dir):
        print "there is no ui dir? ui files not found"
        return
    
    ui_files = [f for f in os.listdir(ui_dir) if os.path.splitext(f)[1] == ".ui"]

    for ui_file in ui_files:
        print "Process %s ..." % ui_file
        subprocess.call([
            'pyuic4.bat',
            '-o',
            os.path.join(plugin_dir, "src", "ui_%s.py" % os.path.splitext(ui_file)[0]),
            os.path.join(ui_dir, ui_file)
        ])


def process_qrc():
    print "process qrc ..."
    qrc_files = [f for f in os.listdir(plugin_dir) if os.path.splitext(f)[1] == ".qrc"]

    for qrc_file in qrc_files:
        print "Process %s ..." % qrc_file
        subprocess.call([
            'pyrcc4',
            '-o',
            os.path.join(plugin_dir, "%s_rc.py" % os.path.splitext(qrc_file)[0]),
            os.path.join(plugin_dir, qrc_file)
        ])


def process_ts():
    print "process ts ..."
    i18n_dir = os.path.join(plugin_dir, "i18n")
    i18n_files = [f for f in os.listdir(i18n_dir) if os.path.splitext(f)[1] == ".ts"]

    for i18n_file in i18n_files:
        print "Process %s ..." % os.path.join(i18n_dir, i18n_file)
        subprocess.call([
            'lrelease',
            os.path.join(i18n_dir, i18n_file)
        ])


def install_plugin():
    print "install plugin ..."
    plugin_install_dir = os.path.join(QGIS_PLUGINS_DIST_DIR, plugin_name)
    if os.path.exists(plugin_install_dir):
        shutil.rmtree(plugin_install_dir)

    print "plugin_dir: ", type(plugin_dir)
    print "plugin_install_dir: ", type(plugin_install_dir)

    shutil.copytree(
        plugin_dir,
        plugin_install_dir,
        ignore=shutil.ignore_patterns(*IGNORE_PATTERNS_FOR_TARGET_INSTALL)
    )


def make_zip():
    print "make zip ..."
    zipFile = zipfile.ZipFile(os.path.join(skript_dir, plugin_name.lower() + ".zip"), 'w')

    src_dir = os.path.join(plugin_dir)

    for root, dirs, files in os.walk(src_dir):
        if root.find('.git') != -1:
            continue

        for f in files:
            if f.endswith(('.gitignore', '.pyc', '.ts', '.qrc', '.sublime-project', '.sublime-workspace', 'Makefile.py', '.zip', 'bat', 'pro')):
                continue
            filename = os.path.join(root, f)
            zipFile.write(filename, os.path.join(plugin_name.lower(), os.path.relpath(filename, src_dir)))


def make_ts_file():
    print "make ts file ..."
    target_files = []
    for root, dirs, files in os.walk(plugin_dir):
        target_files.extend(
            [os.path.join(root, f) for f in files if os.path.splitext(f)[1] in [".ui", ".py"]]
        )

    cmd = ['pylupdate4']
    cmd.extend(target_files)
    cmd.append("-ts")
    cmd.append(os.path.join(plugin_dir, "i18n", TS_FILE_NAME))

    pprint.pprint(cmd)
    subprocess.call(cmd)

if 'rc' in targets:
    process_qrc()

if 'ui' in targets:
    process_ui()

if 'build' in targets:
    process_qrc()
    if BUILD_UI_FOR_TATGET_BUILD:
        process_ui()

if 'install' in targets:
    install_plugin()

if 'ts' in targets:
    make_ts_file()

if 'lang' in targets:
    process_ts()

if 'pack' in targets:
    make_zip()