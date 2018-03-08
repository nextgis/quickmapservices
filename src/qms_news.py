import os
import sys


plugin_dir = os.path.dirname(__file__).decode(sys.getfilesystemencoding())


class News(object):
	"""docstring for News"""
	def __init__(self, html, date_start, date_finish):
		super(News, self).__init__()
		self.html = '<html><head/><body><img src="%s"/>&nbsp;&nbsp;%s</body></html>' % (plugin_dir + '/icons/news.png', html)
		self.date_start = date_start
		self.date_finish = date_finish
