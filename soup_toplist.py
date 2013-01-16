#!/usr/bin/env python3
import urllib.request, urllib.error, re, os.path, sys, time
from optparse import OptionParser
from BeautifulSoup import BeautifulSoup

class post:
    def __init__(self,content,type, date,repostedfrom,via,repostedby, whole):
        self.content = content
        self.date = date
        self.repostedfrom = repostedfrom
        self.repostedby = repostedby
        self.whole = whole
        self.via = via
        self.type = type
        
    def get_rep(self):
        """ Function to return a printable representation for the post, returns
        the original for now """
        return self.whole

def get_posts(tag):
    return tag.has_key('class') and tag['class'].find('post') != -1

def split_page(page):
    begin = page.find("<div id=\"posts\">")
    end = page.find("</div><!--/posts>")
    head,tail = page[:begin], page[end + len("</div><!--/posts>"):]

    posts = page[begin+len("<div id=\"posts\">"):end] 
    return head, BeautifulSoup(posts).findAll(get_posts), tail


def scrape_page(baseurl, starturl="", depth=9999):
    url = baseurl + starturl
    sys.stderr.write("downloading " + url+"\n")
    page = urllib.request.urlopen(url).read().decode("utf-8")
    head, posts, tail = split_page(page)
    # the strong tag shouldn't be needed but apparently non-greedy matching
    # doesn't work and >90% of the page then match
    nextpagere = re.compile("<strong><a href=\"(.*?)\" onclick=\"SOUP.Endless.getMoreBelow")
    g = nextpagere.search(page)
    if g != None:
        starturl = g.group(1)
        for i in range (depth-1):
            url = baseurl + starturl
            try:
                sys.stderr.write("downloading " + url+"\n")
                npage = urllib.request.urlopen(url).read().decode("utf-8")
            except urllib.error.HTTPError as e:
                sys.stderr.write("HTTP Error: " +  str(e.code)  + " " + url + "\n")
                break
            except urllib.error.URLError as e:
                sys.stderr.write("URL Error: " +  str(e.code)  + " " + url + "\n")
                break
            posts.extend(BeautifulSoup(npage).find('div',{'id':'posts'}).findAll(get_posts))
            g = nextpagere.search(npage)
            if g == None:
                break
            starturl = g.group(1)
    return head, posts, tail

def get_reposted_by(tag):
    return tag.has_key('class') and tag['class'].find('reposted_by') != -1

def repost_compare(a):
    return len(a.repostedby) if a.repostedby else 0

def get_statistics(posts):
    sys.stderr.write("getting statistics...")
    timere = re.compile("title=\"(.*)\">")
    userre = re.compile("user_container *(user[0-9]*)")
    viare = re.compile("via<span class=\"user_container (user[0-9]*)")
    typere = re.compile("post_([a-z]*)")
    tops=[]
    i = 0
    for entry in posts:
        i+=1
        print(entry.decode())
        print("*******************")
        type = via = reposts = repostfrom = None
        #get type
        try:
            type = typere.search(entry['class']).group(1)
        except Exception as e:
            print("no type: '" + str(i) + entry['class'] + "' " + entry.decode())
        #get date of post
        timespan = timere.search(entry.div.find('span',{'class':'time'}).decode())
        if timespan != None:
            ts = time.strptime(timespan.group(1), "%b %d %Y %H:%M:%S UTC")
        else:
            sys.stderr.write("Error can't get time of post")
        #contentbody
        contentbody = entry.find('div', {'class':'content-container'}).div
        #reactions
        reposttag = contentbody.find('ul','reactions')
        if reposttag:
            reposttag.decompose()
            
        #get reposted by
        reposttag = contentbody.find(get_reposted_by)
        if reposttag:
            reposts = userre.findall(reposttag.decode())
            reposttag.decompose()
        #get reposted from and via
        reposttag = contentbody.find('div', {'class':'source'})
        if reposttag:
            repostfrom = userre.search(reposttag.span.decode()).group(1)
            viatag = viare.search(reposttag.decode())
            if viatag:
                via = viatag.group(1)
            reposttag.decompose()
        tops.append(post(contentbody, type, ts, repostfrom, via, reposts, entry))
    tops.sort(key=repost_compare)
    sys.stderr.write("done\nfound  "+str(len(tops))+"posts\n")
    sys.stderr.write("generating file...")
    return tops

def get_uid(tag):
    return tag.has_key('href') and tag['class'].find('reposted_by') != -1


def get_output(tops, URL, head):
    appre = re.compile('/appearance/css/')
    head = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
    head += '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">'
    head += appre.sub('http://'+URL+"/appearance/css/",head)
    head += """ <body class="not_edit">
<div id="contentcontainer2">
<div id="contentcontainer" class="groups_hidden">
<div id="content" class="multiple-authors group">

<div id="headercontainer2" class="">
<div id="headercontainer" class="accounts_hidden accounts_empty">
  <div id="header" class="friends_empty">

    <div id="title">
      <div id="h1">
            <h1 class=""><a href="http://""" + URL+ """"
            name="options[title]"> TOP 50 for """ + URL + """</a></h1>
      </div>
    </div>
  </div><!--/header-->
</div><!--/headercontainer-->
</div><!--/headercontainer2-->
<div id="maincontainer">
<div id="main">
  <div id="posts">
"""
    tail="""  
    </div><!--/posts-->
</div><!--/main-->
</div><!--/maincontainer-->
</div><!--/content-->
</div><!--/contentcontainer-->
</div><!--/contentcontainer2-->
</body>
</html>"""
    posts = ""
    for post in tops:
        posts += post.get_rep()
    return head + posts + tail

def main (argv=None):
    URL = "gaf.soup.io"
    topn = 50

    if len(argv) > 3:
        error = "too many arguments\ntry: "+argv[0]+" [<URL>] [<no of posts>]"
        sys.stderr.write(error)
        return 1
    if len(argv) > 2:
        topn = Int(argv[2])
    if len(argv) > 1:
        URL = argv[1]
        if URL.startswith("http://"):
            URL = URL[7:]
    if os.path.exists(URL+".html"):
        sys.stderr.write("reading page locally... ")
        with open(URL+".html","r") as f:
            page = f.read()
        sys.stderr.write("done\nparsing the tree...")
        head,posts,tail = split_page(page)
        sys.stderr.write("done\n")
    else:
        head,posts,tail = scrape_page("http://"+URL, "", 2)
        with open(URL+".html", "w+") as f:
            f.write(head)
            for post in posts:
                f.write(post.decode())
            f.write(tail)
    tops = get_statistics(posts)
    if not tops:
        sys.stderr.write("couldn't get stats")
        sys.exit(1)
    output = get_output(tops[0:topn],URL, head)
    print(output)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
