#!/usr/bin/python3

import csv
import os
import re
from optparse import OptionParser
import urllib
import time
import sys
import requests
from bs4 import BeautifulSoup

headers = {
    "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)\
                AppleWebKit/537.36 (KHTML, like Gecko)\
                Chrome/89.0.4389.114 Safari/537.36"
}

class BColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Google:
    @classmethod
    def search_by_url(self, key, winnowing):
        soup = ""
        with requests.Session() as s:
            key = "\"" + key.strip().replace("\n"," ") + "\""
            key = urllib.parse.quote(key) + "&hl=en"
            url = "https://www.google.com/search?q=" + key
            global headers
            response = s.get(url, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')
        if re.search("No results found for", soup.get_text()) and not winnowing:
            return []
        links = soup.find_all('a',{'href': re.compile('(htt.*://.*)')})
        urls = [re.split(":(?=http)", link.get("href"))[0] for link in links]
        return [url for url in urls if not re.search(r"webcache|google.com|translate.google|support.google|policies.google|search\?hl=en\&q=related", url)]
    @classmethod
    def search_by_api(self, key):
        from googlesearch import search
        return [url for url in search(key, tld="co.in", num=10, stop=10, pause=2)]

def search(key, backend, winnowing, winnow_kgrams, winnow_winsize, delay):
    urls = []
    if backend == "google-search":
        urls = Google.search_by_url(key, winnowing)
    elif backend == "google-api":
        urls = Google.search_by_api(key)
    if winnowing:
        import modules.winnowing as wn
        for url in urls:
            data = extract_text(url)
            plCode, plCode_colored, ratio = wn.plagiarismCheck(key, data, winnow_kgrams, winnow_winsize)
            if plCode != None:
                print(url)
                print("Approx ratio of plagiarized content: ", ratio)
                print(plCode_colored)
            time.sleep(delay)
    return [url for url in urls]

def read_blocks(target, lines):
    blocks = []
    block = [""]
    location_start = 1
    location_end = -1
    counter = 0
    location = 0
    for line in target:
        if counter >= lines and len(block[0]) > 0:
            location_end = location
            block.append(location_start)
            block.append(location_end)
            blocks.append(block)
            block = [""]
            location_start = location + 1
            counter = 0
        if line.strip():
            block[0] += line
        counter += 1
        location += 1
    # Make sure the end block whose lines fewer than expected still included
    if block not in blocks:
        location_end = location
        block.append(location_start)
        block.append(location_end)
        blocks.append(block)
    return blocks

def extract_text(url):
    with requests.Session() as s:
        global headers
        response = s.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()    # rip it out
    # get text
    text = soup.get_text()
    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text

def write_to_html(target, block, data, fw):
    html = """
        <tr>
            <td>""" + target + ":%d-%d" % (block[1], block[2])  + """</td>
            <td>""" + block[0].replace("\n","<br>") + """</td>
            <td>
                <ul>"""
    for url in data:
        html += """
                <li><a href=\""""+url+"""\">"""+url+"""</a></li>"""
    html += """
                </ul>
            </td>
        </tr>
    """
    fw.write(html)

def write_to_csv(target, block, urls, fw):
    data = ""
    for url in urls:
        data += url + "\n"
    value = [target + ":%d-%d" % (block[1], block[2]) , block[0], data]
    writer = csv.writer(fw)
    writer.writerow(value)

def search_and_write(target, block, backend, fw, winnowing, \
                    winnow_kgrams, winnow_winsize, delay, output_format, quiet):
    data = search(block[0].replace("\n", " "), backend, winnowing, winnow_kgrams, winnow_winsize, delay)
    if len(data) == 0:
        time.sleep(delay)
        return
    if not quiet:
        print(f"{BColors.OKCYAN}\nBlock \n'''\n%s\n''' is plagiarized\n{BColors.ENDC}" % block[0])
    if output_format == "html":
        write_to_html(target, block, data, fw)
    elif output_format == "csv":
        write_to_csv(target, block, data, fw)
    time.sleep(delay)

def scan(target, lines, backend, output_format, fw, winnowing, \
        winnow_kgrams, winnow_winsize, delay, quiet):
    if os.path.isdir(os.path.abspath(target)):
        for t in os.listdir(os.path.abspath(target)):
            scan(os.path.join(os.path.abspath(target), t), lines, backend, output_format, \
                            fw, winnowing, winnow_kgrams, winnow_winsize, delay, quiet)
    elif os.path.isfile(os.path.abspath(target)):
        with open(os.path.abspath(target)) as fr:
            for block in read_blocks(fr.readlines(), lines):
                search_and_write(target, block, backend, fw, winnowing, \
                                winnow_kgrams, winnow_winsize, delay, output_format, quiet)
    else:
        for block in read_blocks([line+"\n" for line in target.splitlines()], lines):
            search_and_write(target, block, backend, fw, winnowing, \
                            winnow_kgrams, winnow_winsize, delay, output_format, quiet)

def option_parser():
    parser = OptionParser()
    parser.add_option('-b', '--backend', dest="backend", default="google-search",
                    help="Search backend, choose one in (google-search, google-api)", metavar="BACKEND")
    parser.add_option('--delay', dest="delay", default=5,
                    help="Delay interval per requests", metavar="NUMBER")
    parser.add_option('-l', '--lines', dest="lines", default=1,
                    help="Number of lines per block", metavar="NUMBER")
    parser.add_option('-o', '--output', dest="output", default="result",
                    help="Name of output file", metavar="OUTPUT")
    parser.add_option('--format', dest="format", default="csv",
                    help="Output format, choose one in (csv, html), default is csv", metavar="FORMAT")
    parser.add_option('--winnowing', action="store_true", default=False,
                    help="Use winnow algorithm to analyze results", metavar="BOOLEAN")
    parser.add_option('--winnow-kgrams', dest='winnow_kgrams', default=4,
                    help="Set noise threshold", metavar="NUMBER")
    parser.add_option('--winnow-winsize', dest="winnow_winsize", default=3,
                    help="Window size", metavar="NUMBER")
    parser.add_option('-q','--quiet', action="store_true", default=False,
                    help="Don't print log of checking plagiarism")
    return parser.parse_args()

def main():
    options, args = option_parser()
    backend = options.backend
    delay = int(options.delay)
    lines = int(options.lines)
    winnowing = options.winnowing
    winnow_kgrams = int(options.winnow_kgrams)
    winnow_winsize = int(options.winnow_winsize)
    
    target = ""
    if not sys.stdin.isatty():
        for line in sys.stdin:
            target += line
    elif len(sys.argv) < 2:
        print("No target!")
        exit(1)
    else:
        target = sys.argv[1]
        if not os.path.exists(os.path.abspath(target)):
            print("Target %s does not exist" % (os.path.abspath(target)))
            exit(1)

    if os.path.exists(options.output + "." + options.format):
        os.remove(options.output + "." + options.format)

    # Start scan
    with open(options.output + "." + options.format, "a") as fw:
        if options.format == "html":
            html_header = """
    <table border=1>
        <tr>
            <th>File</th>
            <th>Block</th>
            <th>Found at</th>
        </tr>
        <indent>
        """
            html_footer = """
        </indent>
    </table>
        """
            fw.write(html_header)
            scan(target, lines, backend, options.format, fw, winnowing, \
                winnow_kgrams, winnow_winsize, delay, options.quiet)
            fw.write(html_footer)
        elif options.format == "csv":
            csv_header = ['File', 'Block', 'Found at']
            writer = csv.writer(fw)
            writer.writerow(csv_header)
            scan(target, lines, backend, options.format, fw, winnowing, \
                winnow_kgrams, winnow_winsize, delay, options.quiet)
        else:
            print("Unknown format of output! Choose one in (csv, html)")
            exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Terminated!")
