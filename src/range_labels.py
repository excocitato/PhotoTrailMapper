from PySide import QtCore, QtGui

class QRangeLabels(QtGui.QWidget):
  "Looks after the 2 text labels above the range slider horizontally"
  
  DEFAULT_HEIGHT = 20
  MARGIN = 30
  LABEL_SPACE = 15 
  
  def __init__(self, parent=None, connected_slider=None, value_to_text_fn=str):
    super(QRangeLabels, self).__init__(parent)
    self.value_to_text_fn = value_to_text_fn
    self.lower_label = QtGui.QLabel("1", self)
    self.lower_label.setAlignment(QtCore.Qt.AlignCenter)
    self.upper_label = QtGui.QLabel("2", self)
    self.upper_label.setAlignment(QtCore.Qt.AlignCenter)
    self.connected_slider = None
    self.margin = self.MARGIN
    
    if connected_slider != None:
      self.setConnectedSlider(connected_slider)
      self.onSliderMoved()
      
  def setConnectedSlider(self,connected_slider):
    if self.connected_slider != None:
      self.connected_slider.lowerValueChanged.disconnect(self.onSliderMoved)
      self.connected_slider.upperValueChanged.disconnect(self.onSliderMoved)
      
    self.connected_slider = connected_slider
    self.connected_slider.lowerValueChanged.connect(self.onSliderMoved)
    self.connected_slider.upperValueChanged.connect(self.onSliderMoved)
    

  def sizeHint(self):
    if self.connected_slider != None:
      return QtCore.QSize(self.connected_slider.geometry().width(), self.DEFAULT_HEIGHT)
    else:
      return QtCore.QSize(self.DEFAULT_HEIGHT, self.DEFAULT_HEIGHT)
  
  def onSliderMoved(self, *args):
    "Slider has moved..."
    self.updateLabelPositions()
    
  def updateSingleLabelPos(self, value, label, leftmost=None, rightmost=None):
    #Sort out left/right boundaries and margins
    if leftmost is None:
      leftmost = self.margin
    else:
      leftmost = max(leftmost, self.margin)
      
    if rightmost is None:
      rightmost = self.geometry().width() - self.margin
    else:
      rightmost = min(self.geometry().width() - self.margin, rightmost)
  
    #now work out what the text is
    new_text = self.value_to_text_fn(value)
    if label.text() != new_text:
      label.setText( new_text )
    
    slider_pos = self.connected_slider.sliderPositionFromValue(value)
    
    geom = label.geometry()  # QRect
    
    label_center = geom.center()  # QPoint
    
    if slider_pos < leftmost:
      slider_pos = leftmost
    elif slider_pos > rightmost:
      slider_pos = rightmost
      
    if label_center.x() != slider_pos:
      label_center.setX(slider_pos)
      geom.moveCenter(label_center)
      label.setGeometry(geom)

  def updateLabelPositions(self):
    "Update the positions of the labels relative to the connected slider"
    if self.connected_slider == None:
      return
    
    self.updateSingleLabelPos(self.connected_slider.lower, self.lower_label)
    self.updateSingleLabelPos(self.connected_slider.upper, self.upper_label, leftmost=self.lower_label.geometry().right() + self.LABEL_SPACE)
    
  def resizeEvent(self, resize_event):
    super(QRangeLabels, self).resizeEvent(resize_event)
    self.updateLabelPositions()
    
  def event(self, event):
    "Event handler override to handle QEvent::LayoutRequest events"
    if event.type() == QtCore.QEvent.Type.LayoutRequest:
      self.updateLabelPositions()
      return True
    else:
      return super(QRangeLabels, self).event(event)
    
    
def qBound( _min, value, _max ):
  "Returns value bounded by min and max. This is equivalent to qMax(min, qMin(value, max))."
  return min( _max, max( _min, value ) )

if __name__=="__main__":
  #let's show the window to have a look at it
  from PySide.QtGui import QApplication
  import sys
  import range_slider
  #Create a Qt application
  app = QApplication(sys.argv)

  span_slider = range_slider.QSpanSlider(QtCore.Qt.Orientation.Horizontal)
  span_slider.setFocusPolicy(QtCore.Qt.StrongFocus)
  span_slider.setTickPosition(QtGui.QSlider.TicksBothSides)
  span_slider.setTickInterval(10)
  span_slider.setSingleStep(1)
  span_slider.show()
  
  labels = QRangeLabels(None, span_slider)
  labels.show()
  
  # Enter Qt application main loop
  app.exec_()
  sys.exit()