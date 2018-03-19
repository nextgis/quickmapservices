import os
import sys

from .compat import get_file_dir

plugin_dir = get_file_dir(__file__)


class News(object):
	"""docstring for News"""
	def __init__(self, html, date_start, date_finish):
		super(News, self).__init__()
		self.html = '<html><head/><body><img src="%s"/>&nbsp;&nbsp;%s</body></html>' % (plugin_dir + '/icons/news.png', html)
		self.date_start = date_start
		self.date_finish = date_finish
