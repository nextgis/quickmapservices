import os
import sys
import datetime

from .compat import get_file_dir
from .plugin_locale import Locale

plugin_dir = get_file_dir(__file__)


class News(object):
	"""docstring for News"""
	def __init__(self, qms_news, date_start=None, date_finish=None):
		super(News, self).__init__()

		html = qms_news.get_text(Locale.get_locale())

		self.html = '<html><head/><body><img src="%s"/>&nbsp;&nbsp;%s</body></html>' % (plugin_dir + '/icons/news.png', html)
		self.date_start = date_start
		if self.date_start is None:
			self.date_start = datetime.datetime.now()
		self.date_finish = date_finish

	def is_time_to_show(self):
		if self.date_start > datetime.datetime.now():
			return False

		if self.date_finish is None:
			return True

		return self.date_finish > datetime.datetime.now() 
