import json
from bs4 import BeautifulSoup

file_path = r"C:\Users\Swastika Roy\.gemini\antigravity-ide\brain\1010e73d-9a95-4a45-a2d8-3f884d990cfd\.system_generated\steps\244\content.md"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

html_start = content.find("<!DOCTYPE html>")
if html_start != -1:
    content = content[html_start:]

soup = BeautifulSoup(content, 'html.parser')
nav_menus = soup.find_all('nav')

print(f"Found {len(nav_menus)} nav elements.")
for i, nav in enumerate(nav_menus):
    print(f'\n--- Nav {i} ---')
    for a in nav.find_all('a'):
        text = a.text.strip().replace('\n', ' ')
        if text:
            print(f"{text} -> {a.get('href')}")
