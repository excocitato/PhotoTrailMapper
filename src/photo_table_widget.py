# -*- coding: utf-8 -*-
from PySide import QtGui, QtCore
import math
import sys
import model

class ImgDetails(object):
  "Basic data about an image"
  
  def __init__(self, image_id, filename, camera_make, taken_date, taken_date_type, longitude, latitude, geo_type):
    self.image_id = image_id
    self.filename = filename
    self.camera_make = camera_make
    self.taken_date = taken_date
    self.taken_data_type = taken_date_type
    self.longitude = longitude
    self.latitude = latitude
    self.geo_type = geo_type
    
  def __str__(self):
    if self.taken_data_type == model.ImageTable.DATE_FROM_FILE:
      date_text = "File Date"
    else:
      date_text = "Taken Date"
      
    img_detail_str = """%s\n%s: %s""" % (self.filename, date_text, model.secondsToDateTimeString(self.taken_date))
    
    if self.longitude is not None and self.latitude is not None:
      if self.geo_type == model.ImageTable.GEO_FROM_EXIF:
        geo_str = "EXIF"
      else:
        geo_str = "USER"
      img_detail_str = "%s\n%s GPS Co-ords (%.4f,%.4f)" % (img_detail_str, geo_str, self.latitude, self.longitude)
       
    if self.camera_make == "":
      return img_detail_str
    else:
      return """%s\nCamera: %s""" % (img_detail_str, self.camera_make) 
      
class PhotoTableWidget(QtGui.QAbstractScrollArea):
  "Represents a lazy loading vertical scrolling table/list of photos"

  #signals
  visibleImagesChangedSignal = QtCore.Signal(int,int) #fires first visible index and last visible index
  requestNewImageSetSignal = QtCore.Signal(int,int) #fires when the user has scrolled far enough we want to load more images up
  imageClicked = QtCore.Signal(int) #fires the image index when an image is clicked on by the user
  selectionChanged= QtCore.Signal() #fires when the selected images change
  
  IMG_WIDTH  = 150 #we need fixed sizes of images in order to make this work, pixels
  IMG_HEIGHT = 150
  IMG_MARGIN = 2  #pixels

  ##how many images on either side of current visible set do we want to buffer the scrolling
  #A really high res screen of 2560 x 1440 might have 144 images on screen at any one time
  #Ideally we would like at least one view size on either side of the current visible range
  BUFFER_IMG_NUMBER = 200 

  IMG_FORMAT = "JPG"

  DIM_OPACITY = 0.4
  
  def __init__(self, parent=None):
    super(PhotoTableWidget, self).__init__()
    self.parent = parent
    self.setMouseTracking(True)
    
    self.compass_image = model.getCompassImage()
    self.pin_image = model.getPinImage()
    
    #min sizes
    self.setMinimumWidth(self.IMG_WIDTH + self.IMG_MARGIN * 2)
    self.setMinimumHeight(self.IMG_HEIGHT + self.IMG_MARGIN * 2)

    #init scroll bars
    self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    #horizontally expand as much as possible, vertically the same
    self.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Ignored)
    
    self.first_visible_index = 0 #the first image index that is currently visible in the view area
    self.last_visible_index = 0 #the last image index that is currently visible in the view area

    self.first_loaded_index = 0 #the first index of the currently loaded image data
    self.last_loaded_index = 0 #the last index of the currently loaded image data
    
    # the user can change the time slider to show only picture between 2 dates on the map
    # we indicate that here by colouring the background slightly
    self.first_index_after_date_filter = None  
    self.last_index_after_date_filter = None
    
    self._total_number_images = 0 #this is the total images to scroll through not the total images loaded
    self.loaded_image_list = [] #list of lazily loaded qimages
    self.img_detail_list = [] #list of ImgDetail objects...
    self.background_dim_colour = QtGui.QColor(0xee, 0xee, 0xee)
    self.img_on_mouse_press = None
    self.selected_image_id_list = []
    self.updateTableSize()
    
    #some cached graphics objects
    self._no_brush = QtGui.QBrush(QtCore.Qt.NoBrush)
    #blue pen
    self._blue_pen = QtGui.QPen(QtCore.Qt.SolidLine)
    self._blue_pen.setWidth(2)
    self._blue_pen.setColor(QtCore.Qt.blue)
    
    
  def clear(self):
    self.loaded_image_list = []
    self.selected_image_id_list = []
    self.first_loaded_index = 0
    self.last_loaded_index = 0
    self.first_index_after_date_filter = None  
    self.last_index_after_date_filter = None
    self._updateViewPortSize()
    self.verticalScrollBar().setValue(0)
    self._updateVisibleIndices()

  def dimEarlierPhotosBackground(self, painter):
    if self.first_index_after_date_filter is None:
      return
    
    layout_width = self.viewport().width()
    last_index_dimmed = self.first_index_after_date_filter - 1
      
    last_dimmed_x, last_dimmed_y = self._calcIndexPos(last_index_dimmed)
    last_dimmed_x = last_dimmed_x + self.IMG_WIDTH + self.IMG_MARGIN
    last_dimmed_y = last_dimmed_y - self.IMG_MARGIN # account for img margin....
    
    view_port_height =self._getCurrentHeightOfViewPort()
    view_top = self.verticalScrollBar().value()
    #we have 2 rectangles, one from the beginning full width to the top of last_dimmed_y
    #one from the left to last_dimmed_x
    if last_dimmed_y > view_top:
      painter.fillRect(0, 0, layout_width, min( view_port_height, last_dimmed_y - view_top), self.background_dim_colour)
    
    bot_second_rect = last_dimmed_y + self.IMG_HEIGHT + 2 * self.IMG_MARGIN
    
    if bot_second_rect > view_top:
      top_second_rect = max(0, last_dimmed_y - view_top)
      if self._calculateImagesPerRow() <= 1:
        width = self.viewport().size().width()
      else:
        width = last_dimmed_x
      painter.fillRect(0, top_second_rect, width,  bot_second_rect - top_second_rect - view_top, self.background_dim_colour)
  
  def dimLaterPhotosBackground(self, painter):
    #dim the end
    if self.last_index_after_date_filter is None or self.last_index_after_date_filter >= self.getTotalNumberOfImages():
      return
    
    view_port_height =self._getCurrentHeightOfViewPort()
    view_top = self.verticalScrollBar().value()
    view_bottom = view_top + view_port_height
    layout_width = self.viewport().width()
    
    last_dimmed_x, last_dimmed_y = self._calcIndexPos(self.last_index_after_date_filter)
    last_dimmed_x = last_dimmed_x - self.IMG_MARGIN
    
    if last_dimmed_y + self.IMG_HEIGHT + self.IMG_MARGIN < view_bottom:
      fill_y_top = last_dimmed_y + self.IMG_HEIGHT + self.IMG_MARGIN - view_top
      painter.fillRect(0, last_dimmed_y + self.IMG_HEIGHT + self.IMG_MARGIN - view_top, layout_width, view_port_height - fill_y_top, self.background_dim_colour)
      
    if last_dimmed_y < view_bottom:
      if self._calculateImagesPerRow() <= 1:
        width = layout_width
      else:
        width = layout_width - last_dimmed_x
      painter.fillRect(last_dimmed_x, last_dimmed_y - view_top, width, self.IMG_HEIGHT + 2 * self.IMG_MARGIN, self.background_dim_colour)
    
  def dimBackground(self, painter):
    "Dim the background of the images which are outside the date filter"
    self.dimEarlierPhotosBackground(painter)
    self.dimLaterPhotosBackground(painter)
      
  def _isImageIndexDimmed(self, img_index):
    "Return true if an image_id is being dimmed"
    if self.first_index_after_date_filter is not None and \
       self.last_index_after_date_filter is not None:
      return img_index < self.first_index_after_date_filter or img_index >= self.last_index_after_date_filter
    else:
      return False
      
  def paintEvent(self, paint_event):
    "Override so we paint our images onto the view port with the appropriate offset"
    super(PhotoTableWidget, self).paintEvent(paint_event)
    
    painter = QtGui.QPainter(self.viewport())
    top_view_pos = self.verticalScrollBar().value()
    bottom_view_pos = top_view_pos + self._getCurrentHeightOfViewPort()
    
    # do any background painting
    #self.dimBackground(painter)
    
    for img_index in range(self.first_visible_index, self.last_visible_index + 1):
      list_index = img_index - self.first_loaded_index
      if list_index < 0 or list_index >= len(self.loaded_image_list):
        break
      
      disp_image = self.loaded_image_list[list_index]
      src_width = disp_image.width()
      src_height = disp_image.height()
      
      #work out if any scaling needs to performed
      if src_width > self.IMG_WIDTH or src_height > self.IMG_HEIGHT:
        if src_width >= src_height:
          dest_width = self.IMG_WIDTH
          dest_height = src_height * self.IMG_HEIGHT / src_width
        else:
          dest_width = src_width * self.IMG_WIDTH / src_height
          dest_height = self.IMG_HEIGHT
      else:
        dest_width = src_width
        dest_height = src_height
        
          
      #centre image in the display rectangle with some offsets
      left_offset = 0
      if dest_width < self.IMG_WIDTH:
        left_offset = (self.IMG_WIDTH - dest_width) // 2
        
      top_offset = 0
      if dest_height < self.IMG_HEIGHT:
        top_offset = (self.IMG_HEIGHT - dest_height) // 2
        
      #calculate top left point of paint
      img_left, img_top = self._calcIndexPos(img_index)
      #correct for centering the image
      img_left += left_offset
      img_top += top_offset
      
      img_bottom = img_top + dest_height
      
      if img_top < top_view_pos:
        dest_clip_top = top_view_pos - img_top
        src_clip_top = dest_clip_top * src_height / dest_height
      else:
        dest_clip_top = 0
        src_clip_top = 0
          
      if img_bottom > bottom_view_pos:
        dest_clip_bottom = img_bottom - bottom_view_pos
        src_clip_bottom = dest_clip_bottom * src_height / dest_height
      else:
        dest_clip_bottom = 0
        src_clip_bottom = 0
        
      if dest_clip_bottom > dest_height:
        continue
      
      #draw qimage into correct place on view port correcting for the current scroll position in y
      draw_y = min( bottom_view_pos, max(0, img_top - top_view_pos))
      
      #calculate the rectangle of the qimage we want to draw on the screen
      source_rect = QtCore.QRect(0, src_clip_top, src_width, src_height - src_clip_bottom) #x,y,width,height
      dest_rect = QtCore.QRect(img_left, draw_y, dest_width, dest_height - dest_clip_bottom)
      
      dimmed = self._isImageIndexDimmed(img_index)
        
      if dimmed:
        painter.setOpacity(self.DIM_OPACITY)
        
      painter.drawImage(dest_rect, disp_image, source_rect )
      
      if dimmed:
        painter.setOpacity(1)
      
      #draw selection
      if self.isListIndexSelected(img_index):
        old_brush, old_pen = painter.brush(), painter.pen()
        painter.setBrush(self._no_brush)
        painter.setPen(self._blue_pen)
        painter.drawRect(dest_rect)
        painter.setBrush(old_brush)
        painter.setPen(old_pen)
        
      #draw compass
      if self.doesImgIndexHaveGeoInfo(img_index):
        #choose image
        if self.img_detail_list[img_index - self.first_loaded_index].geo_type == model.ImageTable.GEO_FROM_EXIF:
          icon_image = self.compass_image
        else:
          icon_image = self.pin_image
          
        icon_src_rect = QtCore.QRect(0, 0, icon_image.width(), icon_image.height())
        icon_dest_rect = QtCore.QRect(img_left, img_top - top_view_pos, icon_image.width(), icon_image.height())
        painter.setOpacity(0.7)
        painter.drawImage(icon_dest_rect, icon_image, icon_src_rect)
        painter.setOpacity(1.0)

  def isListIndexSelected(self, img_index):
    "Check if the image at a given list index is selected"
    list_index = img_index - self.first_loaded_index
    if list_index >= 0 and list_index < len(self.img_detail_list):
      return self.img_detail_list[list_index].image_id in self.selected_image_id_list
    else:
      return False
    
  def doesImgIndexHaveGeoInfo(self, img_index):
    list_index = img_index - self.first_loaded_index
    if list_index >= 0 and list_index < len(self.img_detail_list):
      return self.img_detail_list[list_index].longitude is not None and self.img_detail_list[list_index].latitude is not None
    else:
      return False

  def doesImgHaveExifGeoInfo(self, img_index):
    "Return True if an image has geo info associated that comes from exif meta data rather than user specified"
    list_index = img_index - self.first_loaded_index
    if list_index >= 0 and list_index < len(self.img_detail_list):
      return self.img_detail_list[list_index].geo_type == model.ImageTable.GEO_FROM_EXIF and\
             self.img_detail_list[list_index].longitude is not None and self.img_detail_list[list_index].latitude is not None
    else:
      return False
   
  def _updateViewPortSize(self):
    """Call when resized or contents changes, this sets limits on scroll bars and updates internal settings"""
    areaSize = self.viewport().size()

    total_height = self._calculateRequiredHeightOfTable(areaSize.width())
    self.verticalScrollBar().setRange(0, total_height - areaSize.height())
    self.horizontalScrollBar().setRange(0, areaSize.width())
    self._updateVisibleIndices()
    self.viewport().update()

  def resizeEvent(self, event):
    "Called when widget resizes"
    super(PhotoTableWidget, self).resizeEvent(event)
    self._updateViewPortSize()

  def repaintTable(self):
    self.viewport().update()
    
  def scrollToIndex(self, target_image_index):
    "Manually induce the width to scroll to show the target_image_index"
    _, target_y = self._calcIndexPos(target_image_index)
    self.verticalScrollBar().setValue(target_y)
    
  def scrollContentsBy (self, dx, dy ):
    "Override to lazy load when required..."
    super(PhotoTableWidget, self).scrollContentsBy(dx,dy)
    self._updateVisibleIndices()
    #check if we need to get images
    ideal_start_index, ideal_end_index = self.getDesiredBufferedImageRange()
    
    if ideal_start_index - self.first_loaded_index <= - self.BUFFER_IMG_NUMBER or \
       (ideal_start_index < self.BUFFER_IMG_NUMBER and ideal_start_index < self.first_loaded_index ) or \
       ideal_end_index - self.last_loaded_index >= self.BUFFER_IMG_NUMBER or\
       (self.total_number_of_images - ideal_end_index < self.BUFFER_IMG_NUMBER and ideal_end_index > self.last_loaded_index):
      self.requestNewImageSetSignal.emit( ideal_start_index, ideal_end_index )

  def updatePhotos(self, img_list_offset, updated_img_list):
    """Update the current set of loaded photos, the offset is the start point in the complete list
    of the images in updated_img_list
    Each row of updated_img_list should be (image_id, file, camera_make, taken_date, taken_date_type, longitude, latitude, geo_type, thumbnail)
    """
    self.loaded_image_list = [img_row_to_qimage(x, self.IMG_FORMAT) for x in updated_img_list ]
    self.img_detail_list = [ImgDetails(x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7]) for x in updated_img_list]
    self.first_loaded_index = img_list_offset
    self.last_loaded_index = img_list_offset + len( updated_img_list )
    self._updateVisibleIndices(force_emit=True)
    self._updateViewPortSize()

  def updateTableSize(self):
    "update the size of the tables and recalculate visible images..."
    new_height = self._calculateRequiredHeightOfTable(self.geometry().width())
    self._setTotalScrollableHeight(new_height)
    #now update the visible pictures...
    self._updateVisibleIndices()

  def _updateVisibleIndices(self, force_emit=False):
    first = self._calculateTopLeftMostImageIndex()
    last = self._calculateBottomRightMostImageIndex()

    if first != self.first_visible_index or last != self.last_visible_index or force_emit:
      self.first_visible_index = first
      self.last_visible_index = last
      self.visibleImagesChangedSignal.emit( self.first_visible_index, self.last_visible_index)

  def getTotalNumberOfImages(self):
    "Returns total number of images to scroll through not number of images loaded"
    return self._total_number_images

  def setTotalNumberOfImages(self, x):
    if x != self._total_number_images:
      self._total_number_images = x
      self.updateTableSize()

  total_number_of_images = property(getTotalNumberOfImages, setTotalNumberOfImages)

  def getDesiredBufferedImageRange(self):
    "return the image indices we would like to have loaded to buffer the scrolling for the given visible scroll position"
    start_buffer = min( self.total_number_of_images, max(0, self.first_visible_index - self.BUFFER_IMG_NUMBER) )
    end_buffer = min(self.total_number_of_images, self.last_visible_index + self.BUFFER_IMG_NUMBER)
    #want it in chunks of size BUFFER_IMG_NUMBER, but allowing end_buffer to equal total number of images if needs to    
    start_buffer = int( round( float( start_buffer ) / self.BUFFER_IMG_NUMBER) * self.BUFFER_IMG_NUMBER )
    if self.total_number_of_images - end_buffer > self.BUFFER_IMG_NUMBER:
      end_buffer = int( round( float( end_buffer ) / self.BUFFER_IMG_NUMBER) * self.BUFFER_IMG_NUMBER )
    else:
      end_buffer = self.total_number_of_images
    
    return start_buffer, end_buffer

  def getImageDetails(self, image_index):
    """Returns the ImageDetails object for the image_index if this is currently loaded
    Otherwise returns None"""
    list_index = image_index - self.first_loaded_index
    if list_index >= 0 and list_index < len(self.img_detail_list):
      return self.img_detail_list[list_index]
    else:
      return None

  def getCurrentBufferedImageRange(self):
    "return the range of image indices currently loaded"
    return [self.first_loaded_index, self.last_loaded_index]

  def _getTotalScrollableHeight(self):
    return self.verticalScrollBar().maximum() + self.viewport().height()

  def _setTotalScrollableHeight(self, new_height):
    if self.verticalScrollBar().maximum() != new_height - self.viewport().height():
      self.verticalScrollBar().setMaximum(new_height - self.viewport().height() )

  def _getCurrentHeightOfViewPort(self):
    return self.viewport().height()
  
  def _getImageIndexAtWidgetPos(self, x, y):
    """Returns the image index given x, y relative to the widget.
    This adjusts for the scroll value internally"""
    scroll_y = self.verticalScrollBar().value()
    absolute_y = y + scroll_y
    return self._getImageIndexAt(x, absolute_y)
    
  def _getImageIndexAt(self, x, y):
    """Returns the image index if x,y is over an image currently being displayed or None
    Here y is in absolute scroll height (not relative screen height)
    """
    imgs_per_row = self._calculateImagesPerRow()
    centre_offset = ( self.viewport().width() - (imgs_per_row + 1) * self.IMG_MARGIN - imgs_per_row * self.IMG_WIDTH ) / 2
    row_num = (y - self.IMG_MARGIN) / (self.IMG_MARGIN + self.IMG_HEIGHT)
    x_index = (x - centre_offset - self.IMG_MARGIN) / ( self.IMG_MARGIN + self.IMG_WIDTH )
    
    img_index = x_index + row_num * imgs_per_row
    
    #check if the mouse is actually over this index
    if img_index < 0 or img_index >= self.total_number_of_images:
      return None
    
    left_x,top_y = self._calcIndexPos(img_index)
    
    if x >= left_x and x <= left_x + self.IMG_WIDTH and y >= top_y and y <= top_y + self.IMG_HEIGHT:
      return img_index
    else:
      return None
    
  def _calcIndexPos(self, img_index):
    "return the position (x,y) of the image at index"
    imgs_per_row = self._calculateImagesPerRow()
    row_num = img_index // imgs_per_row

    y = (row_num + 1) * self.IMG_MARGIN + row_num * self.IMG_HEIGHT

    x_index = img_index - row_num * imgs_per_row
    
    #centre images in table
    centre_offset = ( self.viewport().width() - (imgs_per_row + 1) * self.IMG_MARGIN - imgs_per_row * self.IMG_WIDTH ) / 2
     
    x = centre_offset + (x_index + 1) * self.IMG_MARGIN + x_index * self.IMG_WIDTH

    return (x,y)

  def _calculateImagesPerRow(self, layout_width=None):
    "Return the number of image per row in this widget for it's current width or for the optional width parameter..."
    if layout_width == None:
      layout_width = float( self.viewport().width() )
    else:
      layout_width = float(layout_width)
    return max(1, int( math.floor( (layout_width - self.IMG_MARGIN) / ( self.IMG_WIDTH + self.IMG_MARGIN ) ) ) )

  def _calculateNumberOfImageRows(self, layout_width=None):
    "Return the number of image rows the table needs for its current width or for the optional width parameter"
    return math.ceil( float(self.total_number_of_images) / self._calculateImagesPerRow(layout_width) ) #total number of rows

  def _calculateRequiredHeightOfTable(self, layout_width=None):
    "Get the total height of the table for all images loaded and unloaded required for its current width or for the optional width parameter"
    num_rows = self._calculateNumberOfImageRows(layout_width)
    if num_rows != 0:
      new_height = ( num_rows + 1 ) * self.IMG_MARGIN + num_rows * self.IMG_HEIGHT
    else:
      new_height = 0
    return new_height

  def _calculateHeightForBufferedImages(self, layout_width=None):
    buffered_rows = math.ceil( len(self.itemList) / self._calculateImagesPerRow(layout_width)) #total number of buffered image rows
    buffered_height = (buffered_rows + 1) * self.IMG_MARGIN + buffered_rows * self.IMG_HEIGHT
    return buffered_height
  
  def _calculateTopLeftMostImageIndex(self):
    "Returns the image index of the current visible top left of the view port"
    num_rows = self._calculateNumberOfImageRows()
    
    if num_rows ==  0:
      return 0
    
    total_height = self._getTotalScrollableHeight()
    scroll_pos = self.verticalScrollBar().value()

    top_row = math.floor( float(scroll_pos) / total_height * num_rows) #this will be zero indexed
    return int( top_row * self._calculateImagesPerRow() )

  def _calculateHeightOfFirstVisibleRow(self):
    "As we scroll down the first visible row effectively get smaller. This is the visible height of the row"
    scroll_pos = self.verticalScrollBar().value()
    row_height = self.IMG_HEIGHT + self.IMG_MARGIN
    return self.IMG_HEIGHT + self.IMG_MARGIN - (scroll_pos % row_height)
    
  def _calculateBottomRightMostImageIndex(self):
    "Returns the image index of the current visible bottom right of the view port"
    num_rows = self._calculateNumberOfImageRows()
    
    if num_rows ==  0:
      return 0
    
    total_height = self._getTotalScrollableHeight()
    bot_scroll_pos = self.verticalScrollBar().value() + self.viewport().height()

    bot_row = math.ceil( float(bot_scroll_pos) / total_height * num_rows) #this will be zero indexed
    return int( bot_row * self._calculateImagesPerRow() )
  
  def mouseMoveEvent(self, evnt):
    "Handle mouse moves and display or not display a tooltip"
    pos = evnt.pos()
    over_img_index = self._getImageIndexAtWidgetPos(pos.x(), pos.y())
    #display the tooltip
    if over_img_index != None:
      txt = self._generateToolTip(over_img_index)
      img_rect = QtCore.QRect(evnt.x(), evnt.y(), self.IMG_WIDTH, self.IMG_HEIGHT)
      QtGui.QToolTip.showText(QtCore.QPoint(evnt.globalX(), evnt.globalY()), txt, self, img_rect) # the tool tip is removed when mouse is outside the given rect
      
  def mousePressEvent(self, evnt):
    "Handle mouse press event"
    pos = evnt.pos()
    self.img_on_mouse_press = self._getImageIndexAtWidgetPos(pos.x(), pos.y())
    
  def mouseReleaseEvent(self, evnt):
    "Handle mouse release event"
    #check if this is a mouse click
    pos = evnt.pos()
    img_on_mouse_release = self._getImageIndexAtWidgetPos(pos.x(), pos.y())
    if img_on_mouse_release is not None and self.img_on_mouse_press == img_on_mouse_release:
      image_id = self.img_detail_list[ img_on_mouse_release - self.first_loaded_index].image_id
      self.imageClicked.emit( image_id )
      # if this image does not have fixed exif geographic user info and not grey out
      #, allow user to select it to
      # set the geo location     
      if not self._isImageIndexDimmed(img_on_mouse_release) and not self.doesImgHaveExifGeoInfo(img_on_mouse_release):
        ctrl_key = QtCore.Qt.KeyboardModifier.ControlModifier == QtGui.QApplication.keyboardModifiers()
        if ctrl_key:
          if image_id in self.selected_image_id_list:
            #unselect
            self.selected_image_id_list.remove(image_id)
          else:
            #select
            self.selected_image_id_list.append(image_id)
        else:
          if image_id in self.selected_image_id_list:
            self.selected_image_id_list = []
          else:
            self.selected_image_id_list = [image_id]
        #fire selection changed
        self.selectionChanged.emit()
    elif len(self.selected_image_id_list) != 0:
      self.selected_image_id_list = []
      self.selectionChanged.emit()
      
    #refresh
    self.repaintTable()  
    #reset
    self.img_on_mouse_press = None
    
  def _generateToolTip(self, img_index):
    list_index = img_index - self.first_loaded_index
    if list_index >= 0 and list_index < len(self.img_detail_list):
      return str(self.img_detail_list[list_index])
    else:
      return ""

def img_row_to_qimage(img_row, _format):
  "Construct a qimage from an image row of data"
  return model.imgdata_to_qimage(img_row[8], _format)
  
if __name__=="__main__":
  app = QtGui.QApplication(sys.argv)
  choose = PhotoTableWidget()
  choose.show()
  sys.exit(app.exec_())