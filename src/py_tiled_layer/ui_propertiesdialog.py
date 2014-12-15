# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\TileLayerPlugin\propertiesdialog.ui'
#
# Created: Fri Aug 29 10:39:32 2014
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(438, 367)
        self.gridLayout = QtGui.QGridLayout(Dialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.gridLayout_2 = QtGui.QGridLayout()
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.buttonBox = QtGui.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Apply|QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout_2.addWidget(self.buttonBox, 3, 0, 1, 1)
        self.groupBox_Style = QtGui.QGroupBox(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_Style.sizePolicy().hasHeightForWidth())
        self.groupBox_Style.setSizePolicy(sizePolicy)
        self.groupBox_Style.setObjectName(_fromUtf8("groupBox_Style"))
        self.verticalLayout = QtGui.QVBoxLayout(self.groupBox_Style)
        self.verticalLayout.setSizeConstraint(QtGui.QLayout.SetDefaultConstraint)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label = QtGui.QLabel(self.groupBox_Style)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.horizontalSlider_Transparency = QtGui.QSlider(self.groupBox_Style)
        self.horizontalSlider_Transparency.setMaximum(100)
        self.horizontalSlider_Transparency.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_Transparency.setObjectName(_fromUtf8("horizontalSlider_Transparency"))
        self.horizontalLayout_3.addWidget(self.horizontalSlider_Transparency)
        self.spinBox_Transparency = QtGui.QSpinBox(self.groupBox_Style)
        self.spinBox_Transparency.setMaximum(100)
        self.spinBox_Transparency.setObjectName(_fromUtf8("spinBox_Transparency"))
        self.horizontalLayout_3.addWidget(self.spinBox_Transparency)
        self.formLayout.setLayout(1, QtGui.QFormLayout.FieldRole, self.horizontalLayout_3)
        self.label_2 = QtGui.QLabel(self.groupBox_Style)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_2)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.comboBox_BlendingMode = QtGui.QComboBox(self.groupBox_Style)
        self.comboBox_BlendingMode.setObjectName(_fromUtf8("comboBox_BlendingMode"))
        self.horizontalLayout.addWidget(self.comboBox_BlendingMode)
        self.label_3 = QtGui.QLabel(self.groupBox_Style)
        self.label_3.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout.addWidget(self.label_3)
        self.formLayout.setLayout(2, QtGui.QFormLayout.FieldRole, self.horizontalLayout)
        self.verticalLayout.addLayout(self.formLayout)
        self.checkBox_SmoothRender = QtGui.QCheckBox(self.groupBox_Style)
        self.checkBox_SmoothRender.setObjectName(_fromUtf8("checkBox_SmoothRender"))
        self.verticalLayout.addWidget(self.checkBox_SmoothRender)
        self.checkBox_CreditVisibility = QtGui.QCheckBox(self.groupBox_Style)
        self.checkBox_CreditVisibility.setObjectName(_fromUtf8("checkBox_CreditVisibility"))
        self.verticalLayout.addWidget(self.checkBox_CreditVisibility)
        self.gridLayout_2.addWidget(self.groupBox_Style, 2, 0, 1, 1)
        self.groupBox_Properties = QtGui.QGroupBox(Dialog)
        self.groupBox_Properties.setObjectName(_fromUtf8("groupBox_Properties"))
        self.gridLayout_3 = QtGui.QGridLayout(self.groupBox_Properties)
        self.gridLayout_3.setObjectName(_fromUtf8("gridLayout_3"))
        self.textEdit_Properties = QtGui.QTextEdit(self.groupBox_Properties)
        self.textEdit_Properties.setReadOnly(True)
        self.textEdit_Properties.setTabStopWidth(80)
        self.textEdit_Properties.setObjectName(_fromUtf8("textEdit_Properties"))
        self.gridLayout_3.addWidget(self.textEdit_Properties, 0, 0, 1, 1)
        self.gridLayout_2.addWidget(self.groupBox_Properties, 0, 0, 1, 1)
        self.gridLayout.addLayout(self.gridLayout_2, 0, 0, 1, 1)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), Dialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "Properties", None))
        self.groupBox_Style.setTitle(_translate("Dialog", "Style", None))
        self.label.setText(_translate("Dialog", "Transparency", None))
        self.label_2.setText(_translate("Dialog", "Blending mode", None))
        self.label_3.setText(_translate("Dialog", "(Default: SourceOver)", None))
        self.checkBox_SmoothRender.setText(_translate("Dialog", "Smoothing", None))
        self.checkBox_CreditVisibility.setText(_translate("Dialog", "Place the credit on the bottom right corner", None))
        self.groupBox_Properties.setTitle(_translate("Dialog", "Properties", None))

