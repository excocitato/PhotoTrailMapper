# -*- coding: utf-8 -*-

from PySide import QtCore, QtGui
from choose_target_dir_widget import ChooseTargetDirWidget
from running_left_widget import RunningLeftWidget
from range_labels import QRangeLabels
from browser_widget import BrowserWidget
from range_slider import QSpanSlider
import os
import version
import ctypes
import file_utils

class RightSideWidget(QtGui.QWidget):
  
  main_html_file = os.path.join( file_utils.getApplicationPath(), 'index.xhtml' )
  
  def __init__(self, parent, start_page_url, js_to_server_call_fn, slider_time_to_date_str_fn):
    super(RightSideWidget, self).__init__(parent)
    
    self.right_side_v_layout = QtGui.QVBoxLayout(self)
    
    slider_layout = QtGui.QVBoxLayout()
    
    self.time_filter_label = QtGui.QLabel("Filter photos between times:")
    slider_layout.addWidget(self.time_filter_label)
    
    self.time_labels = QRangeLabels(parent, value_to_text_fn=slider_time_to_date_str_fn)
    
    # self.time_labels.setSizePolicy()
    slider_layout.addWidget(self.time_labels)
    
    self.time_slider = QSpanSlider(QtCore.Qt.Orientation.Horizontal, self)
    self.time_slider.setToolTip("Only show images on the map in the specified date range.")
    self.time_slider.setMinMaxRange(0, 100)
    self.time_slider.setSingleStep(1)
    self.time_slider.setUpperPosition(self.time_slider.maximum())
    
    slider_layout.addWidget(self.time_slider)
    
    self.right_side_v_layout.addLayout(slider_layout)
    
    tool_layout = QtGui.QHBoxLayout()
    
    #add zoom out button to tools layout
    self.zoom_to_all_btn = QtGui.QPushButton("Zoom Out/See All")
    self.zoom_to_all_btn.setMaximumWidth(150)
    self.zoom_to_all_btn.setToolTip("Zoom out to see all images on the map.")
    
    tool_layout.addWidget(self.zoom_to_all_btn)
    
    #add button to place selected images 
    self.place_selected_btn = QtGui.QPushButton("Place Selected Images")
    self.place_selected_btn.setMaximumWidth(150)
    self.place_selected_btn.setEnabled(False)
    self.place_selected_btn.setToolTip("Place selected images in the centre of current map position")
    
    tool_layout.addWidget(self.place_selected_btn)
    
    #add checkbox to show/hide paths
    self.display_paths_btn = QtGui.QCheckBox("Show Paths")
    self.display_paths_btn.setCheckState(QtCore.Qt.CheckState.Checked)
    self.display_paths_btn.setMaximumWidth(150)
    
    tool_layout.addWidget(self.display_paths_btn)
    
    self.right_side_v_layout.addLayout(tool_layout)
    
    self.time_labels.setConnectedSlider(self.time_slider)
    
    self.webView = BrowserWidget(self, self.main_html_file, js_to_server_call_fn)
    self.webView.initialise()
    
    self.right_side_v_layout.addWidget(self.webView)
    
  def resizeEvent(self, event):
    super(RightSideWidget, self).resizeEvent(event)
    
    desired_browser_size = QtCore.QSize(self.time_slider.width(), 
                                        self.height() - self.webView.geometry().top() )
                                      
    if desired_browser_size.height() > 600:
      desired_browser_size.setHeight(600)
      
    self.webView.frame.page().setViewportSize(desired_browser_size)
    self.webView.frame.page().setPreferredContentsSize(self.webView.frame.page().viewportSize())

class Ui_MainWindow(object):
  "Represents the SETUP of QT main window, not the application code"
  
  def setupUi(self, MainWindow, start_page_url, js_to_server_call_fn):
    MainWindow.setObjectName("MainWindow")
    MainWindow.resize(958, 460)
    MainWindow.setMinimumSize(QtCore.QSize(250, 250))
    
    icon_file = file_utils.getIconFilePath()
    self.setWindowIcon(QtGui.QIcon(icon_file))
    self.setWindowTitle("Photo Trail Mapper Beta %s" % version.getVersionString() )
    if os.name == 'nt':
      # This is needed to display the app icon on the taskbar on Windows 7
      myappid = 'MyOrganization.MyGui.1.0.0' # arbitrary string
      ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
    self.centralWidget = QtGui.QWidget(MainWindow)
    self.centralWidget.setObjectName("centralWidget")
    
    self.top_vertical_layout = QtGui.QVBoxLayout(self.centralWidget)
    self.top_vertical_layout.setObjectName("top_vertical_layout")
    
    # container for choosing directory
    self.choose_dir_widget = ChooseTargetDirWidget(self.centralWidget)
    self.top_vertical_layout.addWidget(self.choose_dir_widget)
    
    # container for main running view in application
    self.running_top_layout = QtGui.QHBoxLayout()
    self.running_top_layout.setObjectName("running_top_layout")
    
    # have a split view between map and picturess
    self.running_splitter = QtGui.QSplitter()
    self.running_splitter.setOrientation(QtCore.Qt.Horizontal)
    self.running_top_layout.addWidget(self.running_splitter)
    
    #widget to hold layout on left of splitter
    self.running_left_split = RunningLeftWidget(self.running_splitter)
    self.photo_table = self.running_left_split.photo_table
    self.running_splitter.addWidget(self.running_left_split)
    
    # right hand side vertical layout
    self.right_side = RightSideWidget(self.running_splitter, start_page_url, js_to_server_call_fn, self._timePercentToFormattedDate)
    self.right_side.setMaximumHeight(10000) 
    self.webView = self.right_side.webView  
    self.time_slider = self.right_side.time_slider
    
    self.running_splitter.addWidget(self.right_side)
    
    split_width = self.running_splitter.size().width()
    self.running_splitter.setSizes([int(split_width / 2), int(split_width / 2)])
    
    self.top_vertical_layout.addLayout(self.running_top_layout)
    MainWindow.setCentralWidget(self.centralWidget)
    
    self.statusLabel = QtGui.QLabel(self.centralWidget)
    self.statusLabel.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Fixed)
    self.top_vertical_layout.addWidget(self.statusLabel)
    
    self.setupActions(MainWindow)
    self.setupMenu(MainWindow)
    QtCore.QMetaObject.connectSlotsByName(MainWindow)

  def _timePercentToFormattedDate(self, value):
    "To be overriden"
    return "Not Implemented"
  
  def setupActions(self, MainWindow):
    self.actionNew = QtGui.QAction("&New", MainWindow, shortcut=QtGui.QKeySequence.New, statusTip="Create a new image set", triggered=MainWindow.onNewFile)  
    self.actionOpen = QtGui.QAction("&Open", MainWindow, shortcut=QtGui.QKeySequence.Open, statusTip="Open an existing image set", triggered=MainWindow.onOpenFile)
    self.actionSave = QtGui.QAction("&Save", MainWindow, shortcut=QtGui.QKeySequence.Save, statusTip="Save the current image set", triggered=MainWindow.onSave)
    self.actionSave.setEnabled(False)
    
    self.actionSave_As = QtGui.QAction("&Save As", MainWindow, shortcut=QtGui.QKeySequence.SaveAs, statusTip="Save the current image set to a specific file", triggered=MainWindow.onSaveAs)
    self.actionSave_As.setEnabled(False)

    self.actionExit = QtGui.QAction("&Exit", MainWindow, shortcut=QtGui.QKeySequence.Quit, statusTip="Exit the program")
    
    self.actionExport_To_CSV = QtGui.QAction("&Export to csv", MainWindow, statusTip="Export file information to csv file", triggered=MainWindow.onExportToCSV)
    self.actionExport_To_CSV.setEnabled(False)
    
    self.actionAbout = QtGui.QAction("&About", MainWindow, triggered=MainWindow.onAbout)
    
  def setupMenu(self, MainWindow):
  
    self.fileMenu = self.menuBar().addMenu("&File")
    self.menuExport = self.menuBar().addMenu("&Export")
    self.menuHelp = self.menuBar().addMenu("&Help")
    
    self.fileMenu.addAction(self.actionNew)
    self.fileMenu.addAction(self.actionOpen)
    self.fileMenu.addAction(self.actionSave)
    self.fileMenu.addAction(self.actionSave_As)
    self.fileMenu.addSeparator()
    self.fileMenu.addAction(self.actionExit)
    
    self.menuExport.addAction(self.actionExport_To_CSV)
    self.menuHelp.addAction(self.actionAbout)

class MainWindow(QtGui.QMainWindow, Ui_MainWindow):
  "The main gui application code, inherits from the setup class"
  
  newFileSignal = QtCore.Signal()
  openFileSignal = QtCore.Signal()
  saveFileSignal = QtCore.Signal()
  saveAsFileSignal = QtCore.Signal()
  exitSignal = QtCore.Signal()
  exportCSVSignal = QtCore.Signal()
  aboutSignal = QtCore.Signal()
  
  def __init__(self, parent=None, start_page_url="index.xhtml", js_to_server_call_fn=None, slider_time_to_formatted_date_fn=None):
    """
    js_server_call_fn which takes func_name, func_params both string, the params json encoded
    """
    super(MainWindow, self).__init__(parent)
    self.slider_time_to_formatted_date_fn = slider_time_to_formatted_date_fn
    self.setupUi(self, start_page_url, js_to_server_call_fn)
    self.showTargetDirectoryScreen()
    self.canExit = False
  
  def _timePercentToFormattedDate(self, value): 
    return self.slider_time_to_formatted_date_fn(value)
  
  def _setRunningWidgetsVisibile(self, visible):
    self.running_splitter.setVisible(visible)
    self.running_left_split.setVisible(visible) 
    self.webView.setVisible(visible)
    self.actionSave.setEnabled(visible)
    self.actionSave_As.setEnabled(visible)
    self.actionExport_To_CSV.setEnabled(visible)
    self.statusLabel.setVisible(visible)
    
  def _setTargetDirectoryWidgetsVisible(self, visible):
    self.choose_dir_widget.setVisible(visible)
    self.actionSave.setEnabled(not visible)
    self.actionSave_As.setEnabled(not visible)
    self.actionExport_To_CSV.setEnabled(not visible)
    self.statusLabel.setVisible(not visible)
    
  def showTargetDirectoryScreen(self):
    "Display a screen where the user can select a top directory to scan under"
    self._setRunningWidgetsVisibile(False)
    self._setTargetDirectoryWidgetsVisible(True)
    
  def showRunningScreen(self):
    self._setRunningWidgetsVisibile(True)
    self._setTargetDirectoryWidgetsVisible(False)
    
  def isRunningScreenShown(self):
    return self.running_left_split.isVisible()
  
  def clearDisplayedData(self):
    self.photo_table.clear()
  
  def onNewFile(self):
    self.newFileSignal.emit()
  
  def onOpenFile(self):  
    self.openFileSignal.emit()
  
  def onSave(self):
    self.saveFileSignal.emit()
  
  def onSaveAs(self):
    self.saveAsFileSignal.emit()
  
  def onExit(self):
    self.exitSignal.emit()
    if self.canExit:
      self.close()
    
  def closeEvent(self, event):
    if not self.canExit:
      #expect self.canExit to be modified during event call....
      self.exitSignal.emit()
  
    if self.canExit:
      event.accept()
    else:
      event.ignore()
    
  def onExportToCSV(self):
    self.exportCSVSignal.emit()
      
  def onAbout(self):
    self.aboutSignal.emit()
    
if __name__ == "__main__":
  # let's show the window to have a look at it
  from PySide.QtGui import QApplication
  import sys
  # Create a Qt application
  app = QApplication(sys.argv)
  main_window = MainWindow()
  main_window.show()
  # Enter Qt application main loop
  app.exec_()
  sys.exit()
