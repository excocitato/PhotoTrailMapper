from PySide import QtCore,QtGui
from photo_table_widget import PhotoTableWidget
import model

class RunningLeftWidget(QtGui.QWidget):
  """This is the left hand side of the splitter, containing the phototable widget and 
  a description of what's visible"""
  
  def __init__(self, parent=None):
    super(RunningLeftWidget, self).__init__(parent)
    
    self.top_layout = QtGui.QVBoxLayout()
    self.setLayout(self.top_layout)
    
    self.photo_table_description = QtGui.QLabel()
    self.photo_table_description.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Fixed)
    self.top_layout.addWidget(self.photo_table_description)
    
    self.photo_table = PhotoTableWidget(self)
    self.top_layout.addWidget(self.photo_table)
    
    #connect to visible pictures changing
    self.photo_table.visibleImagesChangedSignal.connect(self._onVisibleImagesChanged)
    
  @QtCore.Slot(int,int)
  def _onVisibleImagesChanged(self, first_visible_index, last_visible_index):
    #last_visible_index is the last index that could be visible on the screen,
    #this may be past the number of actual images
    last_visible_index = min(last_visible_index, self.photo_table.getTotalNumberOfImages() - 1)
    first_image_data = self.photo_table.getImageDetails(first_visible_index)
    last_image_data = self.photo_table.getImageDetails(last_visible_index)
    
    if first_image_data is not None and last_image_data is not None and \
       first_image_data.taken_date is not None and last_image_data.taken_date is not None:
      
      first_date = model.secondsToDateTimeString(first_image_data.taken_date)
      second_date = model.secondsToDateTimeString(last_image_data.taken_date)
      self.photo_table_description.setText("Displaying images from %s to %s." % (first_date, second_date))
      
    else:
      self.photo_table_description.setText("")
    
