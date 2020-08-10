import webbrowser
import subprocess
import logging
from ulauncher.api.shared.action.BaseAction import BaseAction

# https://docs.python.org/2/library/webbrowser.html

logging.basicConfig()
logger = logging.getLogger(__name__)

class OpenUrlActionExtended(BaseAction):
    """
    Opens URL in a default browser
    :param str url:
    """

    def __init__(self, url, browser_profile):
        self.url = url
        self.browser_profile = browser_profile

    def run(self):
        # logging.info(self.url, self.browser_profile)
        if self.browser_profile["bin"] is None:
            webbrowser.open_new_tab(self.url)
            return

        # currently just chrome browsers supported
        args = [self.browser_profile["bin"], "--profile-directory=", self.browser_profile["profile"], self.url]
        logging.info(args)
        # creationflags=DETACHED_PROCESS,
        pid = subprocess.Popen(args,  close_fds=True).pid
        # shlex.join(
        logging.info(f"running pid={pid}: {0}".format(args))
         
