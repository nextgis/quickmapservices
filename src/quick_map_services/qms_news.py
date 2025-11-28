import datetime
import os
from pathlib import Path

from quick_map_services.core import utils

plugin_dir = os.path.dirname(__file__)


class News:
    """docstring for News"""

    def __init__(
        self, qms_news, date_start=None, date_finish=None, icon="news.png"
    ) -> None:
        super(News, self).__init__()

        html = qms_news.get_text(utils.locale())

        icon_path = Path(plugin_dir) / "icons" / icon

        self.html = """
            <html>
            <head></head>
            <body>
                <center>
                    <table>
                        <tr>
                            <td><img src="{}"></td>
                            <td>&nbsp;{}</td>
                        </tr>
                    </table>
                </center>
            </body>
            </html>
        """.format(icon_path, html)
        self.date_start = date_start
        if self.date_start is None:
            self.date_start = datetime.datetime.now()
        self.date_finish = date_finish

    def is_time_to_show(self):
        current_timestamp = datetime.datetime.now().timestamp()
        if self.date_start.timestamp() > current_timestamp:
            return False

        if self.date_finish is None:
            return True

        return self.date_finish.timestamp() > current_timestamp
