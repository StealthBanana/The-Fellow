from flask import Flask, redirect, render_template, request, url_for, stream_template
import requests
from tubescrape import YouTube, YouTubeError, RateLimitError, ProxyBlockedError
import feedparser
import re

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True


TEACHING_IDEA_FEEDS = {
    "Cult of Pedagogy": "https://www.cultofpedagogy.com/feed/",
    "MiddleWeb": "https://www.middleweb.com/feed/",
    "TeachThought": "https://www.teachthought.com/feed/",
    "WeAreTeachers": "https://www.weareteachers.com/feed/"
}


MAX_IDEAS_PER_SOURCE = 10
# Depending on the API vs time it takes to get information, this may have to be increased or decreased.
FEED_TIMEOUT_SECONDS = 20

@app.route("/", methods=["GET", "POST"])
def input():
    if request.method == "POST":

        topic = request.form.get("inputTopic", "")
        topic = topic.title()

        if not topic:
            return redirect("/")

        return redirect(url_for(('results'), topic=topic))

    else:
        return render_template("index.html")

@app.route("/surprise")
def surprise():
    topic = ""

    url = "https://en.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "format": "json",
        "list": "random",
        "rnnamespace": 0,
        "rnlimit": 1
    }

    headers = {
        "User-Agent": "TheFellow (https://github.com/StealthBanana/The-Fellow)"
    }

    try:
        response = requests.get(
            url=url,
            params=params,
            headers=headers,
            timeout=FEED_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        topic = "Clocks and their uses"
        return redirect(url_for("results", topic=topic))
    except requests.exceptions.RequestException:
        topic = "Requesting data"
        return redirect(url_for("results", topic=topic))
    except ValueError:
        topic = "The importance of values"
        return redirect(url_for("results", topic=topic))

    topic = data["query"]["random"][0]["title"]

    return redirect(url_for("results", topic=topic))

@app.route("/results/<topic>")
def results(topic):

    context = {
        "topic": topic,
        "books": getBooks(topic),
        "podcasts": getPodcasts(topic),
        "videos": getVideos(topic),
        "researchPapers": getResearchPapers(topic),
        "wikiArticles": getWikiArticles(topic),
        "teachingIdeas": getTeachingIdeas(topic),
        "audiobooks": getAudiobooks(topic),
        "images": getImages(topic)
    }

    return stream_template("results.html",**context)


def urlify(topic):
    urlTopic = topic.split()
    urlTopic = "+".join(urlTopic)
    return urlTopic



def getBooks(topic):
    urlTopic = urlify(topic)

    url = ''.join(["https://openlibrary.org/search.json?q=", urlTopic])

    try:
        response = requests.get(url, timeout=FEED_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
       return "Open Library took too long to respond. Try again later."
    except requests.exceptions.RequestException as e:
        return f"Could not reach Open Library right now ({e})."
    except ValueError:
        return "Open Library returned an unexpected response."
    
    return data["docs"]



def getPodcasts(topic):
    urlTopic = urlify(topic)

    url = ''.join(["https://itunes.apple.com/search?term=", urlTopic, "&media=podcast", "&entity=podcast", "&limit=50"])

    try:
        response = requests.get(url, timeout=FEED_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        return "iTunes took too long to respond. Try again later."
    except requests.exceptions.RequestException as e:
        return f"Could not reach iTunes right now ({e})."
    except ValueError:
        return "iTunes returned an unexpected response."

    return data["results"]



def getVideos(topic):
    yt = YouTube()

    try:
        response = yt.search(query=topic, max_results=50, type="video")
    except RateLimitError:
        response = "Rate limited, use a proxy"
        return response
    except ProxyBlockedError:
        response = "Proxy blocked by firewall, use residential proxies"
        return response
    except YouTubeError as e:
        response = "YouTube error: {e}"
        return response

    yt.close()
    
    return response.videos



def getResearchPapers(topic):
    urlTopic = urlify(topic)

    url = f"http://export.arxiv.org/api/query?search_query=all:{urlTopic}&start=0&max_results=50"

    try:
        response = requests.get(url, timeout=FEED_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return "arXiv took too long to respond. Try again later."
    except requests.exceptions.RequestException as e:
        return f"Could not reach arXiv right now ({e})."

    feed = feedparser.parse(response.content)

    if feed.bozo and not feed.entries:
        return "arXiv returned an unexpected response."

    papers = []
    for entry in feed.entries:
        papers.append({
            "title": entry.title,
            "link": entry.id,
            "summary": entry.summary,
            "authors": [author.name for author in entry.authors],
            "published": entry.published
        })
# Keeps html clean by only showing at most 3 authors for resaerch papers that may have many more
    for paper in papers:
        authorRange = len(paper["authors"])
        tempList = []
        if (authorRange > 3):
            for author in range(3):
                tempList.append(paper["authors"][author])
            tempList.append(f"and {authorRange - 3} more")
            paper["authors"] = tempList
        else:
            for i in range(authorRange):
                tempList.append(paper["authors"][i])
            paper["authors"] = tempList

    return papers



def getWikiArticles(topic):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "opensearch",
        "namespace": 0,
        "search": topic,
        "limit": 25,
        "format": "json",
        "warningsaserror": True
    }

    headers = {
        "User-Agent": "TheFellow (https://github.com/StealthBanana/The-Fellow)"
    }

    try:
        response = requests.get(url=url, params=params, headers=headers, timeout=FEED_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        return "Wikipedia took too long to respond. Try again later."
    except requests.exceptions.RequestException as e:
        return f"Could not reach Wikipedia right now ({e})."
    except ValueError:
        return "Wikipedia returned an unexpected response."

    if "error" in data:
        return [{"title": f"API error: {data['error']['info']}", "link": "#"}]

    # Zips titles and links together using zip. 
    # Remember, zip returns tuples that you can use! 
    articles = [{"title": t, "link": l} for t, l in zip(data[1], data[3])]
    return articles



def stripHtml(rawHtml):
    text = re.sub(r"<[^>]+>", " ", rawHtml)
    text = re.sub(r"\s+", " ", text).strip()
    return text



def getTeachingIdeas(topic, maxPerSource=MAX_IDEAS_PER_SOURCE):

    topicWords = [word.lower() for word in topic.split() if len(word) > 2]

    ideasBySource = {}

    headers = {
        "User-Agent": "TheFellow (https://github.com/StealthBanana/The-Fellow)"
    }

    for sourceName, feedUrl in TEACHING_IDEA_FEEDS.items():
        try:
            response = requests.get(feedUrl, headers=headers, timeout=FEED_TIMEOUT_SECONDS)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            ideasBySource[sourceName] = {"error": f"{sourceName} took too long to respond. Try again later."}
            continue
        except requests.exceptions.RequestException as e:
            ideasBySource[sourceName] = {"error": f"Could not reach {sourceName} right now ({e})."}
            continue

        feed = feedparser.parse(response.content)

        # feedparser sets bozo=1 on malformed XML. If it also found zero
        # entries, it will be treated as a dead/broken feed rather than an empty one! Basically is a good failsafe
        if feed.bozo and not feed.entries:
            ideasBySource[sourceName] = {"error": f"{sourceName}'s feed could not be read right now."}
            continue

        matches = []
        for entry in feed.entries:
            title = entry.get("title", "")
            summaryRaw = entry.get("summary", "")
            summary = stripHtml(summaryRaw)

            haystack = f"{title} {summary}".lower()

            if any(word in haystack for word in topicWords):
                matches.append({
                    "title": title,
                    "link": entry.get("link", "#"),
                    "summary": (summary[:300] + "...") if len(summary) > 300 else summary,
                    "published": entry.get("published", "")
                })

            if len(matches) >= maxPerSource:
                break

        ideasBySource[sourceName] = {"entries": matches}

    return ideasBySource



def getAudiobooks(topic):
    urlTopic = urlify(topic)
    url = ''.join(["https://itunes.apple.com/search?term=", urlTopic, "&media=audiobook", "&entity=audiobook", "&limit=50"])

    try:
        response = requests.get(url, timeout=FEED_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        return "iTunes took too long to respond. Try again later."
    except requests.exceptions.RequestException as e:
        return f"Could not reach iTunes right now ({e})."
    except ValueError:
        return "iTunes returned an unexpected response."

    for audiobook in data["results"]:
        audiobook["description"] = re.sub(r"<.*?>", " ", audiobook["description"])


    return data["results"]



def getImages(topic):
    urlTopic = urlify(topic)
    url = "".join(
            [
                "https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=",
                urlTopic,
                "&gsrnamespace=6&prop=imageinfo&iiprop=url|extmetadata&gsrlimit=50&format=json",
            ]
        )
    
    headers = {
        "User-Agent": "TheFellow (https://github.com/StealthBanana/The-Fellow)"
    }

    try:
        response = requests.get(
            url, headers=headers, timeout=FEED_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        return "wikiMedia took too long to respond. Try again later."
    except requests.exceptions.RequestException as e:
        return f"could not reach wikiMedia right now ({e})."
    except ValueError:
        return "wikiMedia returned an unexpected response."

    pages = data.get("query", {}).get("pages", {})
    cc0_licenses = {"cc0", "pd", "public domain", "cc-zero"}

    filtered_results = []
    for page in pages.values():
        image_info = page.get("imageinfo", [{}])[0]
        license_name = (
            image_info.get("extmetadata", {})
            .get("LicenseShortName", {})
            .get("value", "")
            .lower()
        )

        if any(lic in license_name for lic in cc0_licenses):
            filtered_results.append(image_info)
    
    return filtered_results

