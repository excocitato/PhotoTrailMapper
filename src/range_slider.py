from PySide import QtCore, QtGui

class QSpanSlider(QtGui.QSlider):
  """A slider with 2 handles that defines a range"""
  
  MOVEMENT_MODES = (FREE_MOVEMENT, NO_CROSSING, NO_OVERLAPPING) = range(0,3)
  
  HANDLE_TYPES = (NO_HANDLE, LOWER_HANDLE, UPPER_HANDLE) = range(0,3)
  
  #signals
  spanChanged = QtCore.Signal(int,int) #lower, upper
  lowerValueChanged = QtCore.Signal(int)
  upperValueChanged = QtCore.Signal(int)
  
  lowerPositionChanged = QtCore.Signal(int)
  upperPositionChanged = QtCore.Signal(int)
  
  def __init__(self, orientation=QtCore.Qt.Orientation.Vertical, parent=None):
    super(QSpanSlider, self).__init__(orientation, parent)
    
    #tracking boolean is inherited
    #This property holds whether slider tracking is enabled.
    #If tracking is enabled (the default), the slider emits the valueChanged() signal 
    #while the slider is being dragged. 
    #If tracking is disabled, the slider emits the valueChanged() signal only when the user releases the slider.
    self.lower = 0
    self.upper = 0
    self.lowerPos = 0  #If tracking is enabled (the default), this is identical to self.lower
    self.upperPos = 0  #If tracking is enabled (the default), this is identical to self.upper.
    self.offset = 0
    self.position = 0
    self.lastPressed = QSpanSlider.NO_HANDLE
    self.mainControl = QSpanSlider.LOWER_HANDLE
    self.lowerPressed = QtGui.QStyle.SC_None
    self.upperPressed = QtGui.QStyle.SC_None
    self.movement = QSpanSlider.FREE_MOVEMENT
    self.firstMovement = False
    self.blockTracking = False
    
    #setup
    self.rangeChanged.connect( self.updateRange )
    self.sliderReleased.connect( self.movePressedHandle );
    
    
  def initStyleOption(self, style_option, handle=None):
    super(QSpanSlider, self).initStyleOption(style_option)
    
    if handle == QSpanSlider.LOWER_HANDLE:
      style_option.sliderPosition = self.lowerPos
      style_option.sliderValue = self.lower
    else:
      style_option.sliderPosition = self.upperPos
      style_option.sliderValue = self.upper

  def sliderPositionFromValue( self, value ):
    "Given a value on the slider return the pixel position relative to parent that maps to value"
    opt = QtGui.QStyleOptionSlider()
    self.initStyleOption(opt, None) #not sure if this is correct
    
    sliderMin = 0
    sliderMax = 0
    sliderLength = 0
    
    grove_rect = self.style().subControlRect(QtGui.QStyle.CC_Slider, opt, QtGui.QStyle.SC_SliderGroove, self)
    
    sub_rect = self.style().subControlRect(QtGui.QStyle.CC_Slider, opt, QtGui.QStyle.SC_SliderHandle, self)
    
    if self.orientation() == QtCore.Qt.Orientation.Horizontal:
      sliderLength = sub_rect.width()
      sliderMin = grove_rect.x()
      sliderMax = grove_rect.right() - sliderLength + 1
    else:
      sliderLength = sub_rect.height()
      sliderMin = grove_rect.y()
      sliderMax = grove_rect.bottom() - sliderLength + 1
    
    return QtGui.QStyle.sliderPositionFromValue(self.minimum(), self.maximum(), value, sliderMax - sliderMin)
  
  def pixelPosToRangeValue(self, pos):
    opt = QtGui.QStyleOptionSlider()
    self.initStyleOption(opt, None) #not sure if this is correct

    sliderMin = 0
    sliderMax = 0
    sliderLength = 0
    
    grove_rect = self.style().subControlRect(QtGui.QStyle.CC_Slider, opt, QtGui.QStyle.SC_SliderGroove, self)
    
    sub_rect = self.style().subControlRect(QtGui.QStyle.CC_Slider, opt, QtGui.QStyle.SC_SliderHandle, self)
    
    if self.orientation() == QtCore.Qt.Orientation.Horizontal:
      sliderLength = sub_rect.width()
      sliderMin = grove_rect.x()
      sliderMax = grove_rect.right() - sliderLength + 1
    else:
      sliderLength = sub_rect.height()
      sliderMin = grove_rect.y()
      sliderMax = grove_rect.bottom() - sliderLength + 1

    return QtGui.QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), pos - sliderMin,
                                           sliderMax - sliderMin, opt.upsideDown)

  def pick(self, pt):
    "Pick the x/y position based on orientation"
    if self.orientation() == QtCore.Qt.Orientation.Horizontal:
      return pt.x() 
    else:
      return pt.y()

  def subtract_points_by_orientation(self, pt1, pt2):
    if self.orientation() == QtCore.Qt.Orientation.Horizontal:
      return pt1.x() - pt2.x()
    else:
      return pt1.y() - pt2.y()
    
  def handleMousePress(self, pos, get_control, set_control, value, handle):
    opt = QtGui.QStyleOptionSlider()
    self.initStyleOption(opt, handle)
  
    oldControl = get_control()
    
    set_control( self.style().hitTestComplexControl(QtGui.QStyle.CC_Slider, opt, pos, self) )
    sr = self.style().subControlRect(QtGui.QStyle.CC_Slider, opt, QtGui.QStyle.SC_SliderHandle, self)
    
    if get_control() == QtGui.QStyle.SC_SliderHandle:
      self.position = value
      self.offset = self.subtract_points_by_orientation(pos, sr.topLeft())
      self.lastPressed = handle
      self.setSliderDown(True)
      self.sliderPressed.emit()
    
    if get_control() != oldControl:
      self.update(sr)

  def setupPainter(self, painter, orientation, x1, y1, x2, y2):
    highlight = self.palette().color(QtGui.QPalette.Highlight)
    gradient = QtGui.QLinearGradient(x1, y1, x2, y2)
    gradient.setColorAt(0, highlight.darker(120))
    gradient.setColorAt(1, highlight.lighter(108))
    painter.setBrush(gradient)

    if orientation == QtCore.Qt.Orientation.Horizontal:
      painter.setPen( QtGui.QPen(highlight.darker(130), 0) )
    else:
      painter.setPen( QtGui.QPen(highlight.darker(150), 0) )

  def drawSpan(self, painter, rect):
    opt = QtGui.QStyleOptionSlider()
    self.initStyleOption(opt)

    #area
    groove = self.style().subControlRect(QtGui.QStyle.CC_Slider, opt, QtGui.QStyle.SC_SliderGroove, self)
    if opt.orientation == QtCore.Qt.Orientation.Horizontal:
      groove.adjust(0, 0, -1, 0)
    else:
      groove.adjust(0, 0, 0, -1)

    #pen & brush
    painter.setPen( QtGui.QPen( self.palette().color(QtGui.QPalette.Dark).lighter(110), 0))
    
    if opt.orientation == QtCore.Qt.Orientation.Horizontal:
      self.setupPainter(painter, opt.orientation, groove.center().x(), groove.top(), groove.center().x(), groove.bottom())
    else:
      self.setupPainter(painter, opt.orientation, groove.left(), groove.center().y(), groove.right(), groove.center().y())

    #draw groove
    painter.drawRect(rect.intersected(groove))

  def drawHandle(self, painter, handle):
    opt = QtGui.QStyleOptionSlider()
    self.initStyleOption(opt, handle)
    
    opt.subControls = QtGui.QStyle.SC_SliderHandle
    
    if handle == QSpanSlider.LOWER_HANDLE:
      pressed = self.lowerPressed 
    else:
      pressed = self.upperPressed
      
    if pressed == QtGui.QStyle.SC_SliderHandle:
      opt.activeSubControls = pressed
      opt.state |= QtGui.QStyle.State_Sunken

    painter.drawComplexControl(QtGui.QStyle.CC_Slider, opt)

  def triggerAction(self, action, main):
    value = 0
    no = False
    up = False
    _min = self.minimum()
    _max = self.maximum()
    
    if self.mainControl == QSpanSlider.LOWER_HANDLE:
      altControl = QSpanSlider.UPPER_HANDLE 
    else:
      altControl = QSpanSlider.LOWER_HANDLE

    self.blockTracking = True

    if action == QtGui.QAbstractSlider.SliderSingleStepAdd:
      if (main and self.mainControl == QSpanSlider.UPPER_HANDLE) or\
         (not main and altControl == QSpanSlider.UPPER_HANDLE):
          value = qBound(_min, self.upper + self.singleStep(), _max)
          up = True
      else:
        value = qBound(_min, self.lower + self.singleStep(), _max)
    
    elif action == QtGui.QAbstractSlider.SliderSingleStepSub:  
      if (main and self.mainControl == QSpanSlider.UPPER_HANDLE) or\
         (not main and altControl == QSpanSlider.UPPER_HANDLE):
          value = qBound(_min, self.upper - self.singleStep(), _max)
          up = True
      else:
        value = qBound(_min, self.lower - self.singleStep(), _max)
        
    elif action == QtGui.QAbstractSlider.SliderToMinimum:
      value = _min
      if (main and self.mainControl == QSpanSlider.UPPER_HANDLE) or\
         (not main and altControl == QSpanSlider.UPPER_HANDLE):
          up = True
        
    elif action == QtGui.QAbstractSlider.SliderToMaximum:
      value = _max
      if (main and self.mainControl == QSpanSlider.UPPER_HANDLE) or\
         (not main and altControl == QSpanSlider.UPPER_HANDLE):
          up = True
  
    elif action == QtGui.QAbstractSlider.SliderMove:
      if (main and self.mainControl == QSpanSlider.UPPER_HANDLE) or\
         (not main and altControl == QSpanSlider.UPPER_HANDLE):
          up = True
          value = self.upperPos
      else:
          up = False
          value = self.lowerPos
          
    elif action == QtGui.QAbstractSlider.SliderNoAction:
        no = True
        
    else:
        print "QxtSpanSliderPrivate::triggerAction: Unknown action"

    if not no and not up:
      if self.movement == QSpanSlider.NO_CROSSING:
        value = min(value, self.upper)
      elif self.movement == QSpanSlider.NO_CROSSING:
        value = min(value, self.upper - 1)

      if self.movement == QSpanSlider.FREE_MOVEMENT and value > self.upper:
        self.swapControls()
        self.setUpperPosition(value)
      else:
        self.setLowerPosition(value)
  
    elif not no:
      if self.movement == QSpanSlider.NO_CROSSING:
        value = max(value, self.lower)
      elif self.movement == QSpanSlider.NO_CROSSING:
        value = max(value, self.lower + 1)

      if self.movement == QSpanSlider.FREE_MOVEMENT and value < self.lower:
        self.swapControls()
        self.setLowerPosition(value)
      else:
        self.setUpperPosition(value)


    self.blockTracking = False
    self.setLowerValue(self.lowerPos)
    self.setUpperValue(self.upperPos)

  def swapControls(self):
    temp = self.lower
    self.lower = self.upper
    self.upper = temp
    
    temp = self.lowerPressed
    self.lowerPressed = self.upperPressed
    self.upperPressed = temp
      
    if self.lastPressed == QSpanSlider.LOWER_HANDLE:
      self.lastPressed = QSpanSlider.UPPER_HANDLE
    else:
      self.lastPressed = QSpanSlider.LOWER_HANDLE
      
    if self.mainControl == QSpanSlider.LOWER_HANDLE:
      self.mainControl = QSpanSlider.UPPER_HANDLE
    else:
      self.mainControl = QSpanSlider.LOWER_HANDLE

  def updateRange(self, _min, _max):
    pass
  
  def setMinMaxRange(self, _min, _max):
    "Set min and max in one go"
    if self.lower != self.minimum():
      new_low = qBound(_min, self.lower, _max)
    else:
      new_low = _min
      
    if self.upper != self.maximum():
      new_high = qBound(_min, self.upper, _max)
    else:
      new_high = _max
      
    self.setMinimum(_min)
    self.setMaximum(_max)
    self.setSpan(new_low, new_high)

  def movePressedHandle(self):
    if self.lastPressed == QSpanSlider.LOWER_HANDLE:
    
      if self.lowerPos != self.lower:
        main = self.mainControl == QSpanSlider.LOWER_HANDLE
        self.triggerAction(QtGui.QAbstractSlider.SliderMove, main)
    
    elif self.lastPressed == QSpanSlider.UPPER_HANDLE:
      
      if self.upperPos != self.upper:
        main = self.mainControl == QSpanSlider.UPPER_HANDLE
        self.triggerAction(QtGui.QAbstractSlider.SliderMove, main)
  
  def handleMovementMode(self):
    return self.movement
    
  def setHandleMovementMode(self, mode):
    self.movement = mode
    
  def lowerValue(self):
    return min(self.lower, self.upper);
    
  def upperValue(self):
    return max(self.lower, self.upper);
    
  def lowerPosition(self):
    return self.lowerPos
    
  def upperPosition(self):
    return self.upperPos
    
  def setLowerValue(self, lower):
    self.setSpan(lower, self.upper);
    
  def setUpperValue(self, upper):
    self.setSpan(self.lower, upper);
    
  def setSpan(self, lower, upper):
    low = qBound(self.minimum(), min(lower, upper), self.maximum())
    upp = qBound(self.minimum(), max(lower, upper), self.maximum())
    
    if low != self.lower or upp != self.upper:
 
        if low != self.lower:
          self.lower = low
          self.lowerPos = low
          self.lowerValueChanged.emit(low)
       
        if upp != self.upper:
            self.upper = upp
            self.upperPos = upp
            self.upperValueChanged.emit(upp)
         
        self.spanChanged.emit(self.lower, self.upper)
        self.update()

  def setLowerPosition(self, lower):
    if self.lowerPos != lower:
      self.lowerPos = lower
      if not self.hasTracking():
        self.update()
        
      if self.isSliderDown():
        self.lowerPositionChanged.emit(lower)
        
      if self.hasTracking() and not self.blockTracking:
        main = self.mainControl == QSpanSlider.LOWER_HANDLE
        self.triggerAction(QtGui.QAbstractSlider.SliderMove, main)

    
  def setUpperPosition(self, upper):
    if self.upperPos != upper:
      self.upperPos = upper;
      if not self.hasTracking():
        self.update()
          
      if self.isSliderDown():
        self.upperPositionChanged.emit(upper)
        
      if self.hasTracking() and not self.blockTracking:    
        main = self.mainControl == QSpanSlider.UPPER_HANDLE
        self.triggerAction( QtGui.QAbstractSlider.SliderMove, main )
  
  def _getStepActionFwd(self):
    if not self.invertedAppearance():
      return QtGui.QAbstractSlider.SliderSingleStepAdd
    else:
      return QtGui.QAbstractSlider.SliderSingleStepSub
      
  def _getStepActionBack(self):
    if not self.invertedAppearance():
      return QtGui.QAbstractSlider.SliderSingleStepSub
    else:
      return QtGui.QAbstractSlider.SliderSingleStepAdd
      
  #over-rides
  def keyPressEvent(self, key_event):
    super( QSpanSlider, self ).keyPressEvent(key_event)

    main = True;
    action =  QtGui.QAbstractSlider.SliderNoAction
    
    if key_event.key() == QtCore.Qt.Key_Left:
        main   = self.orientation() == QtCore.Qt.Orientation.Horizontal
        action = self._getStepActionBack()
    
    elif key_event.key() == QtCore.Qt.Key_Right:
        main   = self.orientation() == QtCore.Qt.Orientation.Horizontal
        action = self._getStepActionFwd()

    elif key_event.key() == QtCore.Qt.Key_Up:
        main   = self.orientation() == QtCore.Qt.Orientation.Vertical
        action = self._getStepActionFwd()
        
    elif key_event.key() == QtCore.Qt.Key_Down:
        main   = self.orientation() == QtCore.Qt.Orientation.Vertical
        action = self._getStepActionBack()
        
    elif key_event.key() == QtCore.Qt.Key_Home:
        main   = self.mainControl == QSpanSlider.LOWER_HANDLE
        action = QtGui.QAbstractSlider.SliderToMinimum
        
    elif key_event.key() == QtCore.Qt.Key_End:
        main   = self.mainControl == QSpanSlider.UPPER_HANDLE
        action = QtGui.QAbstractSlider.SliderToMaximum
        
    else:
        key_event.ignore()

    if action:
      self.triggerAction(action, main)
    
  def getUpperPressed(self):
    return self.upperPressed
  
  def setUpperPressed(self, x):
    self.upperPressed = x
    
  def getLowerPressed(self):
    return self.lowerPressed
  
  def setLowerPressed(self, x):
    self.lowerPressed = x
    
  def mousePressEvent(self, mouse_event):
    if self.minimum() == self.maximum() or mouse_event.buttons() ^ mouse_event.button():
      mouse_event.ignore()
      return

    self.handleMousePress(mouse_event.pos(), self.getUpperPressed, self.setUpperPressed, self.upper, QSpanSlider.UPPER_HANDLE)
    
    if self.upperPressed != QtGui.QStyle.SC_SliderHandle:
      #likewise lowerPressed
      self.handleMousePress(mouse_event.pos(), self.getLowerPressed, self.setLowerPressed, self.lower, QSpanSlider.LOWER_HANDLE )

    self.firstMovement = True
    mouse_event.accept();
    
  def mouseMoveEvent(self, mouse_event):
    if self.lowerPressed != QtGui.QStyle.SC_SliderHandle and self.upperPressed != QtGui.QStyle.SC_SliderHandle:
        mouse_event.ignore()
        return;
    
    opt = QtGui.QStyleOptionSlider()
    self.initStyleOption(opt)
    
    m = self.style().pixelMetric(QtGui.QStyle.PM_MaximumDragDistance, opt, self)
    
    newPosition = self.pixelPosToRangeValue(self.pick(mouse_event.pos()) - self.offset)
    
    if m >= 0:
      r = self.rect().adjusted(-m, -m, m, m)
      if not r.contains(mouse_event.pos()):
        newPosition = self.position

    # pick the preferred handle on the first movement
    if self.firstMovement:
      if self.lower == self.upper:
    
        if newPosition < self.lowerValue():
          self.swapControls()
          self.firstMovement = False
          
      else:
        self.firstMovement = False
  
    if self.lowerPressed == QtGui.QStyle.SC_SliderHandle:
      if self.movement == QSpanSlider.NO_CROSSING:
        newPosition = min(newPosition, self.upperValue())
          
      elif self.movement == QSpanSlider.NO_OVERLAPPING:
        newPosition = min(newPosition, self.upperValue() - 1)

      if self.movement == QSpanSlider.FREE_MOVEMENT and newPosition > self.upper:
        self.swapControls()
        self.setUpperPosition(newPosition)
      else:
        self.setLowerPosition(newPosition)
        
    elif self.upperPressed == QtGui.QStyle.SC_SliderHandle:

      if self.movement == QSpanSlider.NO_CROSSING:
        newPosition = max(newPosition, self.lowerValue())
      elif self.movement == QSpanSlider.NO_OVERLAPPING:
        newPosition = max(newPosition, self.lowerValue() + 1)

      if self.movement == QSpanSlider.FREE_MOVEMENT and newPosition < self.lower:
          self.swapControls()
          self.setLowerPosition(newPosition)
      else:
          self.setUpperPosition(newPosition)

    mouse_event.accept()
    
  def mouseReleaseEvent(self, mouse_event):
    super(QSpanSlider, self).mouseReleaseEvent(mouse_event)
    self.setSliderDown(False)
    self.lowerPressed = QtGui.QStyle.SC_None
    self.upperPressed = QtGui.QStyle.SC_None
    self.update()
    
  def paintEvent(self, paint_rvent):
    painter = QtGui.QStylePainter(self);

    #groove & ticks
    opt = QtGui.QStyleOptionSlider()
    self.initStyleOption(opt)
    opt.sliderValue = 0
    opt.sliderPosition = 0
    opt.subControls = QtGui.QStyle.SC_SliderGroove | QtGui.QStyle.SC_SliderTickmarks
    painter.drawComplexControl(QtGui.QStyle.CC_Slider, opt)

    #handle rects
    opt.sliderPosition = self.lowerPos
    lr = self.style().subControlRect(QtGui.QStyle.CC_Slider, opt, QtGui.QStyle.SC_SliderHandle, self)
    lrv  = self.pick(lr.center())
    opt.sliderPosition = self.upperPos
    ur = self.style().subControlRect(QtGui.QStyle.CC_Slider, opt, QtGui.QStyle.SC_SliderHandle, self)
    urv = self.pick(ur.center())

    # span
    minv = min(lrv, urv)
    maxv = max(lrv, urv);
    c = QtCore.QRect(lr.center(), ur.center()).center()
    spanRect = QtCore.QRect()
    if self.orientation() == QtCore.Qt.Orientation.Horizontal:
      spanRect = QtCore.QRect(QtCore.QPoint(minv, c.y() - 2), QtCore.QPoint(maxv, c.y() + 1))
    else:
      spanRect = QtCore.QRect(QtCore.QPoint(c.x() - 2, minv), QtCore.QPoint(c.x() + 1, maxv))
    self.drawSpan(painter, spanRect)

    #handles
    if self.lastPressed == QSpanSlider.LOWER_HANDLE:
      self.drawHandle(painter, QSpanSlider.UPPER_HANDLE)
      self.drawHandle(painter, QSpanSlider.LOWER_HANDLE)
    else:
      self.drawHandle(painter, QSpanSlider.LOWER_HANDLE)
      self.drawHandle(painter, QSpanSlider.UPPER_HANDLE)

def qBound( _min, value, _max ):
  "Returns value bounded by min and max. This is equivalent to qMax(min, qMin(value, max))."
  return min( _max, max( _min, value ) )

if __name__=="__main__":
  #let's show the window to have a look at it
  from PySide.QtGui import QApplication
  import sys
  #Create a Qt application
  app = QApplication(sys.argv)

  span_slider = QSpanSlider(QtCore.Qt.Orientation.Horizontal)
  span_slider.setFocusPolicy(QtCore.Qt.StrongFocus)
  #span_slider.setTickPosition(QtGui.QSlider.TicksBothSides)
  #span_slider.setTickInterval(10)
  span_slider.setSingleStep(1)
  span_slider.setMinMaxRange(0,100000000)
  span_slider.setLowerValue(0)
  span_slider.setUpperValue(10000000)
  span_slider.show()
  
  # Enter Qt application main loop
  app.exec_()
  sys.exit()
