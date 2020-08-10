import os
import sys
import json
import logging
from glob import glob
from os import sys, path
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent, PreferencesEvent, PreferencesUpdateEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction

from ulauncher.api.client.EventListener import EventListener
import importlib
import subprocess
import shlex
from pprint import pprint
from shutil import which
from urllib.parse import urljoin, urlparse
import os
from string import Template
from gi.repository import Gio,GLib, Gtk
from ulauncher.utils.mypy_extensions import TypedDict
from ulauncher.config import CACHE_DIR

# allow these imports to be undefined
try:
    import pyjq
    from fuzzywuzzy import fuzz 
    import sqlite3
except:
    pass


logging.basicConfig()
logger = logging.getLogger(__name__)

def create_temporary_copy(path):
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, 'temp_file_name')
    shutil.copy2(path, temp_path)
    return temp_path

"""
BookmarkItem = TypedDict('BookmarkItem', {
    'id': str,
    'type': str,
    'name': str,
    'description': str,
    'options': OptionItems,
    'default_value': str,
    'user_value': str,
    'value': str,
})
BookmarkItems = List[BookmarkItem]
"""

def get_firefox_bookmarks(sqlite_path, use_temp=False):
    bookmarks = []
    try:
        if use_temp:
            sqlite_path = create_temporary_copy(sqlite_path)
        firefox_connection = sqlite3.connect(
            'file:' + sqlite_path + '?mode=ro', 
            uri=True, isolation_level=None, timeout=0.2
        )
        cursor = firefox_connection.cursor()
        cursor.execute("""select url, moz_bookmarks.title,  last_visit_date from moz_places join moz_bookmarks on moz_bookmarks.fk=moz_places.id order by dateAdded desc;""")
        for row in cursor:
            link = row[0]
            title = row[1]
            bookmarks.append({"title": title, "url": link})
        cursor.close()
        if use_temp:
            os.remove(sqlite_path)
    except Exception as error:
        logger.error("{0}: {1}".format(type(error), str(error)))
        if isinstance(error, sqlite3.OperationalError) or str(error) == "database is locked":
            logger.info("Retrying with temporary copy of database")
            return get_firefox_bookmarks(sqlite_path, use_temp=True)
        else:
            raise error


def format_path_str(template, *args, **kw_args):
    d = dict(os.environ)
    kw_dict = {}
    # insert dicts
    if len(args) > 0:
        for dict_arg in args:
            if isinstance(dict_arg, (dict)):
                kw_dict.update(dict(dict_arg))
            else:
                raise ValueError('type {0} could not be converted'.format(type(dict_arg))) 
    kw_dict = dict(kw_dict, **kw_args)
    if len(kw_args) > 0:
        for k,v in kw_args.items():
            if isinstance(v, (str, int)):
                d[k] = v
            else:
                raise ValueError('key {0}, type {0} could not be converted'.format(k, type(v))) 
    d.update(kw_dict)
    return Template(template).substitute(d)


class PreferencesEventListener(EventListener):
    def on_event(self, event, extension):
        print("1")
        pprint(event.preferences)
        extension.set_preferences(event.preferences)

class PreferencesUpdateEventListener(EventListener):
    def on_event(self, event, extension):
        p = extension.preferences.copy()
        p[event.id] = event.new_value
        extension.set_preferences(p)


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        return extension.get_results(event.get_argument())

class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()

        browser_profile = data["browser_profile"] or {};
        url = data["url"]
        bin = browser_profile["bin"]

        # logging.info(data.url, data.browser_profile)
        if bin is None:
            # webbrowser.open_new_tab(url)
            # use  GTK default browser
            # /desktop/gnome/url-handlers/http/command
            Gtk.show_uri_on_window(None, url, Gdk.CURRENT_TIME)
            return

        # currently just chrome browsers supported
        args = [browser_profile["bin"], "--profile-directory=" + browser_profile["profile"], url]
        logging.info("launching %s" % args)

        # on windows: creationflags=DETACHED_PROCESS = 0x00000008
        pid = subprocess.Popen(args,  close_fds=True).pid

        # output for copy and pasta
        logging.info("running pid={0}: {1}".format(pid, shlex.join(args)))
        return DoNothingAction()


class BrowserBookmarks(Extension):

    gtk_theme = ""
    bookmark_files = []
    bookmarks = []
    bms = [{
        "origin": ""
        "browser_config"
    }]

    # keys do map 
    browser_config_old = {
        "chromium": ["chromium-browser", "chromium-browser-beta"],
        "google-chrome":  ["google-chrome", "google-chrome-beta"],
        "brave":  ["brave", "brave-beta"]
    }

    title_tpl = "${title}"
    description_tpl = "${profile} | ${url}"

    browser_configs = {
        "chromium": {
            "kind": "chrome",
            "config_path": "${HOME}/.config/chromium",
            "bins": ["chromium-browser", "chromium-browser-beta",  "chromium-browser-dev"],
            "args": ["${bin}", "--profile-directory=${profile}", "${url}"]
        },
        "google-chrome": {
            "kind": "chrome",
            "config_path": "${HOME}/.config/google-chrome",
            "bins": ["google-chrome", "google-chrome-beta", "google-chrome-dev"],
            "args": ["{bin}", "--profile-directory=${profile}", "${url}"]
        },
        "brave": {
            "kind": "chrome",
            "config_path": "${HOME}/.config/brave",
            "bins": ["brave", "brave-beta"],
            "args": ["${bin}", "--profile-directory=${profile}", "${url}"]
        },
        "firefox": {
            "kind": "firefox",
            "config_path": "${HOME}/.mozilla",
            "bins": ["firefox", "firefox-beta"],
            "args": ["${bin}", "-P", "${profile}", "${url}"]
            # update-alternatives --list x-www-browser
        }
    }

    def __init__(self):
        super(BrowserBookmarks, self).__init__()
        self.check_dynamic_modules()
        self.bookmark_files = self.find_bookmark_files()
        self.results = []
        self.last_error = None
        self.gtk_theme = Gtk.IconTheme.get_default()
        self.set_preferences ({
            'keyword': 'bm',
            'title': self.title_tpl,
            'description': self.description_tpl
        })
        self.update_cache()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(PreferencesEvent, PreferencesEventListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesUpdateEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

    @staticmethod
    def check_dynamic_modules():
        for module in ("pyjq", "fuzzywuzzy"):
            if not importlib.util.find_spec(module): 
                self.last_error = {
                    'msg': f"Python module '{module}' was not found",
                    'desc': u"Please install this module by pip and restart ULauncher",
                }

    def find_bookmark_files(self):
        home = os.environ['HOME']
        config_pathes = []
        for browser_key, browser_config in self.browser_configs.items():
            p = format_path_str(browser_config['config_path'])
            if browser_config['kind'] != "chrome":
                continue

            # for sqlite_path in glob('/home/ctang/.mozilla/firefox/*/places.sqlite'):
            if path.exists(p):
                config_pathes.append(p)

        bookmark_pathes = []
        for config_path in config_pathes:
            bookmark_pathes += glob(f'{config_path}/*/Bookmarks')
        pprint(config_pathes)
        browser_types = {} # browser config folder names
        bookmarks = []
        for bookmark_path in bookmark_pathes:
            bookmark_path_split = bookmark_path.split("/");
            browser_type = bookmark_path_split[-3]
            bin = None
            if browser_type in browser_types:
                bin = browser_types.get(browser_type)
            else:
                if browser_type in BrowserBookmarks.browser_config_old:
                    for test_bin in BrowserBookmarks.browser_config_old[browser_type]:
                        print("{0} {1} {2}".format(browser_type, test_bin, which(test_bin)))
                        if bin is None:
                            bin = which(test_bin)
                            
                if bin is None:
                    bin = which(browser_type)
                browser_types[browser_type] = bin
            bookmarks.append({
                "browser_type": browser_type,
                "bin": bin,
                "profile": bookmark_path_split[-2],
                "last_modification": os.path.getmtime(bookmark_path),
                "path": bookmark_path,
            })
        logger.info("browser config to bin %s" % browser_types)

        if len(bookmarks) == 0:
            self.last_error = {
                'msg': "No Bookmark files",
                'desc': u"No bookmark files could be found from browsers",
            }

        return bookmarks

    def get_icon_default(self, icon_name, fallback=None):
        icon = Gtk.IconTheme.lookup_icon(self.gtk_theme, icon_name, 0, 0)
        if not icon and fallback:
            return fallback;
        if not icon:
            return 'images/error.svg';
        return icon.get_filename()

    def open_url(url, profile):
        profile["bin"]
        profile["profile"]

    def set_preferences(self, p):
        self.preferences = p

    def notify(self, msg, desc):
        return RenderResultListAction([ExtensionResultItem(
            icon='images/error.svg',
            name=msg.encode('utf8'),
            description=desc.encode('utf8')
        )])

    def get_results(self, query):
        if self.last_error is not None:
            return self.notify(**self.last_error)

        bookmark_icon = self.get_icon_default(
            'bookmark',
            'images/bookmark.svg'
        )

        items = []
        for i, item in enumerate(self.match(query)):
            if i > 10:
                break
            bookmark = item['bookmark']
            print( bookmark['browser_profile']['browser_type'])
            icon = self.get_icon_default(
                bookmark['browser_profile']['browser_type'], 
                bookmark_icon
            )
            items.append(ExtensionResultItem(
                icon=icon,
                name=bookmark['name'],
                description=bookmark['browser_profile']['profile'] + '|' + bookmark['url'],
                on_enter=ExtensionCustomAction(bookmark),
                on_alt_enter=ExtensionCustomAction(bookmark)
            ))
        return RenderResultListAction(items)

    

    def update_cache(self):
        self.last_error = None
        self.bookmarks = []

        for bookmark_file in self.bookmark_files:
            filepath = bookmark_file["path"]
            try:
                with open(filepath) as f:
                    content = json.load(f)
            except:
                self.last_error = {
                    'msg': "Failed to open file '{}'".format(filepath),
                    'desc': u"Check that file exists and is readable",
                }
                break

            logging.info(f"Loading bookmarks from {filepath}")
            for item in pyjq.all('.roots | .. | select(.type? == "url" and .url? != null) | with_entries(select(.key == ("url", "name", "date_added")))',content):
                if len(item['url']) == 0:
                    continue
                url = item['url'];
                url_without_params = urljoin(url, urlparse(url).path).lower()

                self.bookmarks.append({
                    'key': item.get('name', '').lower() + '|' + url_without_params,
                    'url': item['url'],
                    'name': item.get('name', ''),
                    'browser_profile': bookmark_file
                })

        self.results = [{
            'char': None,
            'scored_items': [{'bookmark': b, 'score': 0} for b in self.bookmarks],
        }]
        logging.info("Total bookmarks loaded %d" % len(self.bookmarks))

    def match(self, query):
        if query is None:
            query = ''
        if len(query) < 1:
            return []

        prev_query = ''.join([r['char'] for r in self.results[1:]])
        common_prefix = os.path.commonprefix([prev_query, query])
        self.results = self.results[:len(common_prefix) + 1]
        query_suffix = query[len(common_prefix):]

        for c in query_suffix:
            items = []
            for item in self.results[-1]['scored_items']:
                bookmark = item['bookmark']
                score = fuzz.partial_token_sort_ratio(bookmark['key'], query)
                items.append({
                    'bookmark': bookmark,
                    'score': score,
                })
            items = sorted(items, key=lambda i: i['score'], reverse=True)
            items = items[:int(len(items))]
            self.results.append({
                'char': c,
                'scored_items': items
            })

        return self.results[-1]['scored_items']


