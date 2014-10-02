# -*- coding: utf-8 -*-

from PySide import QtGui, QtCore
import qt_utils
import os
import file_utils

class ChooseTargetDirWidget(QtGui.QWidget):
  "Represents the gui setup for controls for choosing the target directory"

  #signals
  directorySelectedSignal = QtCore.Signal(str) #Fires file path to top level directory (that exists!)

  def __init__(self, parent=None):
    super(ChooseTargetDirWidget, self).__init__()

    self.parent = parent
    self.initUI()

  def initUI(self):
    self.setObjectName("choose_dir_widget")
    self.setMinimumSize(QtCore.QSize(250, 20))
    self.setMaximumSize(QtCore.QSize(2000, 80))

    #container for choosing directory
    self.select_directory_layout = QtGui.QHBoxLayout()
    self.select_directory_layout.setObjectName("select_directory_layout")

    self.directory_label = QtGui.QLabel(self)

    font = qt_utils.createStandardFont()

    self.directory_label.setFont(font)
    self.directory_label.setObjectName("directory_label")

    self.select_directory_layout.addWidget(self.directory_label)

    self.directory_edit_box = QtGui.QLineEdit(self)
    self.directory_edit_box.setObjectName("directory_edit_box")
    self.directory_edit_box.returnPressed.connect(self._return_pressed)

    #debug
    self.directory_edit_box.setText(file_utils.getMyPicturesPath())
    #debug

    self.select_directory_layout.addWidget(self.directory_edit_box)

    self.directory_browse_button = QtGui.QPushButton(self)
    self.directory_browse_button.setToolTip("")
    self.directory_browse_button.setText("...")
    self.directory_browse_button.setObjectName("directory_browse_button")
    self.select_directory_layout.addWidget(self.directory_browse_button)

    self.select_directory_button = QtGui.QPushButton(self)
    self.select_directory_button.setObjectName("select_directory_button")
    self.select_directory_button.setText("OK")
    self.select_directory_layout.addWidget( self.select_directory_button )

    self.directory_label.setText("Select top directory to scan...")


    self.setLayout( self.select_directory_layout )

    ##connect events
    self.directory_browse_button.clicked.connect(self._onDirectoryBrowse)
    self.select_directory_button.clicked.connect(self._onDirectoryOK)

  @QtCore.Slot()
  def _return_pressed(self):
    self._onDirectoryOK()
    
  @QtCore.Slot()
  def _onDirectoryBrowse(self):
    folder = qt_utils.choose_folder( self, "Top Target Folder", self.directory_edit_box.text() )
    if folder != None:
      self.directory_edit_box.setText( folder )

  @QtCore.Slot()
  def _onDirectoryOK(self):
    folder = self.directory_edit_box.text()
    if os.path.exists( folder ) and os.path.isdir( folder ):
      self.directorySelectedSignal.emit( folder )
    else:
      qt_utils.show_error_msg(self, "%s is not a valid directory." % folder )


if __name__=="__main__":
  import sys
  app = QtGui.QApplication(sys.argv)
  choose = ChooseTargetDirWidget()
  choose.show()
  sys.exit(app.exec_())