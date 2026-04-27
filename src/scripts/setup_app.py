from setuptools import setup
import py2app
import sys
import os

# Copier le script menu_app.py dans un accessible location
script_path = os.path.join(os.path.dirname(__file__), 'tools', 'menu_app.py')
app = py2app.App(
    script=script_path,
    name="ProjectHub",
    iconfile="icon.png",
    plist={
        'LSUIElement': True,  # Ne pas apparaître dans le Dock
        'CFBundleDisplayName': "Project Hub",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0",
        'CFBundleIdentifier': "com.user.macosgithubprojects",
    },
    options={
        'argv_emulation': False,
        'iconfile': 'icon.png',
        'plist': 'Info.plist',
    }
)