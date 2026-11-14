import urllib.request, shutil
vids = [
    ('1053155855', 'c:\\\\turnpike\\\\frontend\\\\turnpike-insight-suite-main\\\\public\\\\tech-1.mp4'),
    ('1063642399', 'c:\\\\turnpike\\\\frontend\\\\turnpike-insight-suite-main\\\\public\\\\tech-2.mp4'),
    ('1030019273', 'c:\\\\turnpike\\\\frontend\\\\turnpike-insight-suite-main\\\\public\\\\tech-3.mp4')
]
for vid, path in vids:
    req = urllib.request.Request(f'https://www.shutterstock.com/shutterstock/videos/{vid}/preview/stock-footage-{vid}.webm', headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response, open(path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print("Downloaded", vid)
    except Exception as e:
        print("Failed", vid, e)
