
from  gi import require_version
require_version('Gdk', '3.0')
require_version('Notify', '0.7')
from BrowserBookmarks import BrowserBookmarks

if __name__ == '__main__':
    BrowserBookmarks().run()
