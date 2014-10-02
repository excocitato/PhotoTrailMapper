from PySide import QtCore, QtGui
import version
import file_utils
import qt_utils

class AboutWindow(QtGui.QDialog):
  "Displays the about window"
  
  def __init__(self, parent):
    super(AboutWindow,self).__init__(parent)
    self.setModal(True)
    self.setMinimumSize(QtCore.QSize(250,250))
    self.setWindowTitle("About")
    
    self.top_vertical_layout = QtGui.QVBoxLayout()
    self.top_vertical_layout.setAlignment(QtCore.Qt.AlignHCenter)
    self.setLayout(self.top_vertical_layout)
    
    title_layout = QtGui.QHBoxLayout()
    title_label = QtGui.QLabel("Photo Trail Mapper")
    title_label.setFont(qt_utils.createStandardFont(size=18))
    title_label.setAlignment(QtCore.Qt.AlignHCenter)
    title_layout.addWidget(title_label)
    self.top_vertical_layout.addLayout(title_layout)
    
    icon_file = file_utils.getIconFilePath()
    icon_label = QtGui.QLabel()
    pixmap = QtGui.QPixmap(icon_file)
    pixmap = pixmap.scaled( QtCore.QSize(200, 200), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation )
    icon_label.setPixmap(pixmap)
    self.top_vertical_layout.addWidget(icon_label)
    
    #TODO remove beta
    version_label = QtGui.QLabel("Version: BETA " + version.getVersionString())
    version_label.setFont(qt_utils.createStandardFont(size=14))
    version_label.setAlignment(QtCore.Qt.AlignHCenter)
    self.top_vertical_layout.addWidget(version_label)
    
    #ok_button = QtGui.QPushButton("OK")
    #ok_button.clicked.connect( self.onOK )
    #ok_button.setMaximumSize(QtCore.QSize(50,50))
    #self.top_vertical_layout.addChildWidget(ok_button)
    
  def onOK(self, *params):
    self.close()
  
if __name__ == "__main__":
  # let's show the window to have a look at it
  from PySide.QtGui import QApplication
  import sys
  # Create a Qt application
  app = QApplication(sys.argv)
  main_window = AboutWindow(None)
  main_window.show()
  # Enter Qt application main loop
  app.exec_()
  sys.exit()