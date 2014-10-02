import sys
from PySide.QtGui import QApplication
from controller import Controller
        
class ExifMain(object):
  "Main object"
   
  def __init__(self):
    self.controller = None
    
  def main(self):
    "Main loop"
    app = QApplication(sys.argv)
    self.controller = Controller()
    self.controller.run()
    app.exec_()

def main():
  try:
    e = ExifMain()
    e.main()
  except:
    import traceback
    traceback.print_exc()
  return 0
  
if __name__ == "__main__":
  main()