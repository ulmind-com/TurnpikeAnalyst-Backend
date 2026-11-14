import re
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_heading = False
        self.in_title = False
        self.headings = []
        
    def handle_starttag(self, tag, attrs):
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5']:
            self.in_heading = True
        if tag == 'title':
            self.in_title = True
            
    def handle_endtag(self, tag):
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5']:
            self.in_heading = False
        if tag == 'title':
            self.in_title = False
            
    def handle_data(self, data):
        text = data.strip()
        if text and (self.in_heading or self.in_title):
            self.headings.append(text)

with open('c:/turnpike/turnpike_live.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()
    
parser = MyHTMLParser()
parser.feed(html)

for h in parser.headings:
    print(h)
