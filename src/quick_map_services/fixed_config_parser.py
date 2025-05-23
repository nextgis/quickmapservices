from configparser import RawConfigParser

DEFAULTSECT = "DEFAULT"


class FixedConfigParser(RawConfigParser):
    """
    Unicode writer fix for ConfigParser
    """

    def write(self, fp, space_around_delimiters: bool = True):
        """Write an .ini-format representation of the configuration state."""
        if self._defaults:
            fp.write("[%s]\n" % DEFAULTSECT)
            for key, value in self._defaults.items():
                fp.write("%s = %s\n" % (key, str(value).replace("\n", "\n\t")))
            fp.write("\n")
        for section in self._sections:
            fp.write("[%s]\n" % section)
            for key, value in self._sections[section].items():
                if key == "__name__":
                    continue
                if (value is not None) or (self._optcre == self.OPTCRE):
                    key = " = ".join((key, str(value).replace("\n", "\n\t")))
                fp.write("%s\n" % (key))
            fp.write("\n")
