import urllib.request, json, re
req = urllib.request.Request('https://www.youtube.com/results?search_query=cyber+security+hacker+typing+laptop+loop', headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req).read().decode('utf-8')
    matches = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
    vids = []
    for vid in set(matches):
        try:
            oembed = urllib.request.urlopen('https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=' + vid).read()
            vids.append(vid)
            if len(vids) >= 3:
                break
        except Exception:
            pass
    print("FOUND EMBEDDABLE:", vids)
except Exception as e:
    print(e)
