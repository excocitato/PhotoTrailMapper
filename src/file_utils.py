import os
import tempfile
import unittest
import sys
from win32com.shell import shell, shellcon

def getMyPicturesPath():
  "Return path to current users My Pictures directory"
  return shell.SHGetFolderPath(0, shellcon.CSIDL_MYPICTURES, None, 0)

def getIconFilePath():
  icon_file = os.path.join(getApplicationPath(), 'camera_pin_icon.ico')
  return icon_file

def getDefaultSaveFolder():
  "Return default folder to save things into"
  return os.getenv('HOME')

def createOpenedTempNamedFile():
  "Creates a temporary file that MUST be deleted explicitly"
  onum, filename = tempfile.mkstemp()
  return FDOpenFile(os.fdopen(onum,"w"), filename)

def getFilenameFromPath(p):
  "Return the filename from the full path"
  dirname, filename = os.path.split(p)
  if len(filename) != 0:
    return filename
  else:
    return dirname
    
def getApplicationPath():
  "Return the path to the application"
  if getattr(sys, 'frozen', False):
    # The application is frozen
    return os.path.dirname(sys.executable)
  else:
    # The application is not frozen
    # Change this bit to match where you store your data files:
    return os.path.dirname(__file__)

class FDOpenFile(object):
  """Class that wraps a file object and only changes the name parameter
  Useful because os.fdopen created file objects have meaningless names!"""
   
  def __init__(self, wrapped_file, file_name):
    self.name = file_name
    self.wrapped_file = wrapped_file
    
  def __getattribute__(self,name):
    if name == "name":
      return object.__getattribute__(self, name)
    elif name == "wrapped_file":
      return object.__getattribute__(self, name)
    elif hasattr(self.wrapped_file, name):
      return object.__getattribute__(self.wrapped_file, name)
    else:
      return object.__getattribute__(self,name)
    
    
class testUtils(unittest.TestCase):
  
  def testTempFile(self):
    t = createOpenedTempNamedFile()
    self.assertTrue( os.path.exists(t.name) )
    self.assertFalse(t.closed)
    t.write("hello")
    t.close()
    os.remove(t.name)
    
    
if __name__=="__main__":
  unittest.main()

    