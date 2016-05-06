__author__ = 'yellow'


class ConfigReaderHelper:

    @staticmethod
    def try_read_config(parser, section, param, reraise=False):
        try:
            val = parser.get(section, param)
        except:
            if reraise:
                raise
            else:
                val = None
        return val

    @staticmethod
    def try_read_config_int(parser, section, param, reraise=False):
        try:
            val = parser.getint(section, param)
        except:
            if reraise:
                raise
            else:
                val = None
        return val

    @staticmethod
    def try_read_config_bool(parser, section, param, reraise=False):
        try:
            val = parser.getboolean(section, param)
        except:
            if reraise:
                raise
            else:
                val = None
        return val