import random
import time
from datetime import datetime

ips = [
    "68.180.224.225", "65.55.213.74", "65.55.213.73", "46.105.14.53",
    "207.241.237.227", "217.212.224.181", "192.95.12.193"
]

urls = [
    "/blog/tags/ipcp", "/blog/tags/open%20source", "/blog/tags/sysadmin",
    "/about/", "/blog/geekery/insist-on-better-asserts.html",
    "/blog/geekery/installing-windows-8-consumer-preview.html",
    "/blog/tags/ruby", "/blog/tags/linux", "/blog/tags/log"
]

agents = [
    "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)",
    "msnbot/2.0b (+http://search.msn.com/msnbot.htm)",
    "UniversalFeedParser/4.2-pre-314-svn +http://feedparser.org/",
    "Mozilla/5.0 (compatible; special_archiver/3.1.1 +http://www.archive.org/details/archive.org_bot)",
    "psbot/0.1 (+http://www.picsearch.com/bot.html)"
]

def generate_log_entry():
    ip = random.choice(ips)
    timestamp = datetime.utcnow().strftime('%d/%b/%Y:%H:%M:%S +0000')
    method = "GET"
    url = random.choice(urls)
    status = 200
    size = random.randint(1000, 40000)
    referer = "-"
    agent = random.choice(agents)
    return f'{ip} - - [{timestamp}] "{method} {url} HTTP/1.1" {status} {size} "{referer}" "{agent}"'

# Generate and print logs continuously
while True:
    print(generate_log_entry())
    time.sleep(1)  # Generate a log every 1 second (you can adjust this)
