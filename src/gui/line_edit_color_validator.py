import re

class LineEditColorValidator(object):

    def __init__(self, line_edit, re_mask, error_color='#f6989d', error_tooltip=''):
        self.error_color = error_color
        self.error_msg = error_tooltip
        self.line_edit = line_edit
        self.line_edit.textChanged.connect(self.on_changed)
        self.re_mask = re_mask
        self.re_comp = re.compile(self.re_mask)
        self.on_changed()  # init

    def is_valid(self):
        text = self.line_edit.text()
        return self.re_comp.match(text)

    def on_changed(self, text=''):
        if self.is_valid():
            self.set_normal_style()
        else:
            self.set_error_style()

    def set_normal_style(self):
        self.line_edit.setStyleSheet('')
        self.line_edit.setToolTip('')

    def set_error_style(self):
        self.line_edit.setStyleSheet('QLineEdit { background-color: %s }' % self.error_color)
        self.line_edit.setToolTip(self.error_msg)






