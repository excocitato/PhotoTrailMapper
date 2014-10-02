from PySide import QtGui
import os
import model

def createStandardFont(size=12):
  "Create standard font for normal text"
  font = QtGui.QFont()
  font.setFamily("Arial")
  font.setPointSize(size)
  return font

def askYesNoQuestion(parent, question, caption):
  "Ask a yes/no question returns True/False"
  reply = QtGui.QMessageBox.question(parent, caption, question, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
  return reply == QtGui.QMessageBox.Yes

def show_error_msg(parent, msg, title="Photo Trail Mapper"):
  "Show a message in an error message box with just an OK button"
  msgBox = QtGui.QMessageBox(parent)
  msgBox.setWindowTitle(title)
  msgBox.setText(msg)
  msgBox.setIcon(QtGui.QMessageBox.Critical)
  msgBox.exec_()
  
def show_warning_msg(parent, msg, title="Photo Trail Mapper"):
  "Show a message with a warning message box with just an OK button"
  msgBox = QtGui.QMessageBox(parent)
  msgBox.setWindowTitle(title)
  msgBox.setText(msg)
  msgBox.setIcon(QtGui.QMessageBox.Warning)
  msgBox.exec_()
  
def show_msg(parent, msg, title="Photo Trail Mapper"):
  "Show a message with just an OK button"
  msgBox = QtGui.QMessageBox(parent)
  msgBox.setWindowTitle(title)
  msgBox.setText(msg)
  msgBox.setIcon(QtGui.QMessageBox.Information)
  msgBox.exec_()

def choose_folder(parent, query_msg, start_dir):
  "Choose a folder returns None if cancelled or non-existant"
  dir_name = QtGui.QFileDialog.getExistingDirectory(parent, query_msg, start_dir, QtGui.QFileDialog.ShowDirsOnly)
  
  if os.path.exists(dir_name):
    return dir_name
  else:
    return None
  
def create_bxf_file_filter():
  return "Batch Scan File (*." + model.Consts.db_file_extension + ")" 

def create_csv_file_filter():
  return "CSV File (*.csv)"

def choose_save_file(parent, current_file, save_filter = None, file_ext = None):
  """Called to show save dialog in QT thread from javascript connection, returns None if cancelled
  current_file can be None
  save_filter specifies the extension filter"""
  if save_filter is None:
    save_filter = create_bxf_file_filter()
  
  if file_ext is None:
    file_ext = model.Consts.db_file_extension
  
  dialog = QtGui.QFileDialog(parent)
  dialog.setFileMode(QtGui.QFileDialog.AnyFile)
  dialog.setNameFilter( save_filter )
  dialog.setAcceptMode(QtGui.QFileDialog.AcceptSave)
  if current_file is not None:
    dialog.setDirectory(os.path.dirname(current_file))
  
  if dialog.exec_():
    file_name = dialog.selectedFiles()[0]  
    file_ext = "." + file_ext
    if file_name[-1 * len(file_ext):].lower() != file_ext.lower():
      file_name = "%s%s" % (file_name,file_ext)
    return file_name
  else:
    return None
  
def choose_open_file(parent):
  "Called to show open dialog in QT thread from javascript connection, , returns None if cancelled"
  dialog = QtGui.QFileDialog(parent)
  dialog.setFileMode(QtGui.QFileDialog.ExistingFile)
  dialog.setNameFilter(create_bxf_file_filter())
  if dialog.exec_():
    file_name = dialog.selectedFiles()[0]
    return file_name
  else:
    return None
  