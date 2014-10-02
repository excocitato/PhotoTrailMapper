import sys
import json
import traceback
from PySide import QtCore
import model
from mainwindow import MainWindow
import version
import exif
import qt_utils
import map_marker_logic
from datetime import datetime
import about

class Controller(QtCore.QObject):
  """This controller is responsible for feeding data from the model to the gui
  and vice versa, as well as owning the worker thread that scans image directories"""
  
  MAP_MARKER_IMG_WIDTH = 75
  MAP_MARKER_IMG_HEIGHT = 75
  
  VIEW_REFRESH_MS = 2000  # only update the gui at this rate in milliseconds when gathering data
  SLIDER_REFRESH_MS = 150
  _THREAD_WAIT_MS = 1000
  
  HELP_URL = "http://www.lococitato.com/exif_mapper/help.html"
  
  def __init__(self, parent=None):
    super(QtCore.QObject, self).__init__(parent)
    ##TODO check for internet connection (display warning if none as can't get map data)
    
    ##TODO check for updates to the application
    
    #data
    self.db_manager = model.DBManager(version.getVersionString())
    self.view_data = model.ViewData()
    self.scanner_thread = None
    self.main_window = MainWindow( js_to_server_call_fn=self._onCallFromBrowserWidget, slider_time_to_formatted_date_fn=self._format_slider_time)
    self.main_window.showTargetDirectoryScreen()
    
    self.photo_table = self.main_window.photo_table
    self.time_slider = self.main_window.time_slider
    #internal settings
    self.view_refresh_count = 0
    self.slider_event_count = 0
    self.accept_new_images = False  # guard against queued images
    self.show_paths = True
    self._last_idlatlng_list = []
    self._last_arrow_list = []
    
    #calls we can receive from the html part of the gui (BrowserWidget)
    self.server_api = {"mapMoved": self._mapMoved,
                       "getImageData": self._getImageData,
                       "mapPhotoHighlighted": self._mapPhotoHighlighted,
                       "imagesDragged": self._imagesDragged }
    
    #connect to the GUI
    self._connectToGUI()
  
  def displayError(self, msg):
    #TODO do something more sensible
    print msg
    
  def displayWaitDialog(self, msg):
    "Show a modal wait dialog while background processing happens"
    pass
  
  def closeWaitDialog(self):
    pass
    
  def _connectToGUI(self):
    "Managed the connection to gui events"
    self.main_window.choose_dir_widget.directorySelectedSignal.connect( self._onDirectorySelected )
    self.main_window.photo_table.requestNewImageSetSignal.connect( self._onRequestNewImageSet )
    self.main_window.photo_table.imageClicked.connect( self._onImageClicked )
    self.main_window.photo_table.selectionChanged.connect( self._onImageSelectionChanged )
    self.main_window.newFileSignal.connect( self._onNewFile )
    self.main_window.openFileSignal.connect( self._onOpenFile )
    self.main_window.saveFileSignal.connect( self._onSaveFile )
    self.main_window.saveAsFileSignal.connect( self._onSaveAsFile )
    self.main_window.exitSignal.connect( self._onExitRequest )
    self.main_window.exportCSVSignal.connect( self._onExportCSV )
    self.main_window.aboutSignal.connect( self._onAbout )
    
    self.main_window.right_side.zoom_to_all_btn.clicked.connect( self._onZoomOutToAll )
    self.main_window.right_side.place_selected_btn.clicked.connect( self._onPlaceSelectImages )
    self.main_window.right_side.display_paths_btn.stateChanged.connect( self._onShowPathChanged )
    
    self.time_slider.spanChanged.connect( self._onTimeSpanChanged )
    
  @QtCore.Slot()
  def _onImageSelectionChanged(self):
    "When the image selection changes update state of place button"
    self.main_window.right_side.place_selected_btn.setEnabled( len(self.photo_table.selected_image_id_list) != 0 )
    
  @QtCore.Slot(int)
  def _onImageClicked(self, image_index):
    """The image has been clicked. If it has a geo-location lets move to it on the map"""
    image_data = self.db_manager.getImageById(image_index)
    
    if image_data.latitude is not None and image_data.longitude is not None:
      self._web_send("panMapTo(%.6f, %.6f);" % (image_data.latitude, image_data.longitude))
    
  @QtCore.Slot(int, int)
  def _onRequestNewImageSet(self, ideal_start_index, ideal_end_index):
    "The user has scrolled far enough the photo widget wants to load more images into the buffer"
    self._updatePhotoTable(buffered_range=(ideal_start_index, ideal_end_index))
    
  @QtCore.Slot(str)
  def _onDirectorySelected(self, directory):
    "User has selected directory and is ready to go"
    try:
      self.db_manager.newFile()
      
      self.view_data = self.db_manager.getViewData()
      self.view_data.current_image_set_info.start_scan_date = datetime.now()
      self.view_data.current_image_set_info.top_folder = directory
      self.db_manager.saveViewData(self.view_data)
      
      self.main_window.showRunningScreen()
      self._stopScanTask()
      self._startScanTask(directory)
    except Exception, e:
      self.displayError(str(e) + "\n" + traceback.format_exc())
    
  @QtCore.Slot()
  def _onNewFile(self):
    self._stopScanTask()
    self.db_manager.newFile()
    self.view_data = self.db_manager.getViewData()
    self.main_window.showTargetDirectoryScreen()
    self.photo_table.clear()
  
  @QtCore.Slot()
  def _onOpenFile(self):
    
    target_file = qt_utils.choose_open_file(self.main_window)
    
    if target_file == None:
      return
    
    try:
      self._stopScanTask()
      self.db_manager.loadFile(target_file)
      self.view_data = self.db_manager.getViewData()
      #tell the gui we are starting#tell the gui we are starting
      self.main_window.showRunningScreen()
      self.main_window.clearDisplayedData()
      self._updateGUIView()
      #need to set the time filters on the range...
      self.main_window.time_slider.setLowerValue(model.dateToSeconds(self.view_data.map_settings.map_start_date))
      self.main_window.time_slider.setUpperValue(model.dateToSeconds(self.view_data.map_settings.map_end_date))
      #TODO Need to reset the map position...
    except Exception, e:
      self.displayError("Unable to load file %s, not what was expected.<br/>%s" % (target_file, str(e)))
  
  def _saveToFile(self, target_file):
    "Perform the actual save"
    try:
      self.db_manager.saveViewData(self.view_data) #save current view positions
      self.db_manager.saveFile(target_file)
      return True
    except Exception, e:
      self.displayError("Unable to save to file %s. %s" % (target_file, str(e)))
      return False
    
  @QtCore.Slot()
  def _onSaveFile(self):
    qt_utils.show_warning_msg(self.main_window, "Saving scans to file is not available in this beta version.")
    #check if we know where to save the data?
    if self.db_manager.saved_to_file == None or len(self.db_manager.saved_to_file) == 0:
      return self._onSaveAsFile()
    else:
      return self._saveToFile(self.db_manager.saved_to_file)

  @QtCore.Slot()
  def _onSaveAsFile(self):
    qt_utils.show_warning_msg(self.main_window, "Saving scans to file is not available in this beta version.")
    return
    target_file = qt_utils.choose_save_file(self.main_window, self.db_manager.saved_to_file)
    if target_file != None:
      return self._saveToFile(target_file)
    else:
      return False
      
  @QtCore.Slot()
  def _onExitRequest(self):
    #check if there is unsaved data....
    if self.db_manager.dirty:
      if qt_utils.askYesNoQuestion(self.main_window, "Save current scan data?", "Save?"):
        while not self._onSaveFile():
          pass  
    self._stopScanTask()
    # allow exit to continue
    self.main_window.canExit = True
    self.db_manager.close()
  
  @QtCore.Slot()
  def _onExportCSV(self):
    "Export the database to csv..."
    #choose a csv file to export too...
    target_file = qt_utils.choose_save_file(self.main_window, None, qt_utils.create_csv_file_filter(), "csv")
    if target_file is not None:
      self.displayWaitDialog("Exporting in cvs format to %s" % target_file)
      try:
        model.exportImageDataToCSV(self.db_manager.cursor, target_file)
      except Exception, e:
        self.displayError(str(e))
      finally:
        self.closeWaitDialog()
      
  @QtCore.Slot()
  def _onAbout(self):
    about_window = about.AboutWindow(self.main_window)
    about_window.show()
  
  @QtCore.Slot(str, str)
  def _onCallFromBrowserWidget(self, func_name, params):
    "Handle a call from the HTML/javascript embedded browser"
    try:
      func_param_dict = json.loads(params)
       
      #find matching function
      server_fn = self.server_api.get(func_name, None )
      
      if server_fn == None:
        print "Unknown function: %s" % func_name
        return
       
      #make the call
      server_fn(func_param_dict)
    except Exception:
      self.displayError( "Exception processing request on server %s with args %s" % (func_name, params) )
      traceback.print_exc()

    
  def _format_slider_time(self, value):
    return model.secondsToDateString(self._slider_time_to_seconds(value))
  
  def _slider_time_to_seconds(self, value):
    "Slider time is in percent"
    min_date = model.dateToSeconds(self.view_data.current_image_set_info.min_date)
    max_date = model.dateToSeconds(self.view_data.current_image_set_info.max_date)
    return min_date + (max_date - min_date) * value / 100
   
  @QtCore.Slot(int)
  def _onShowPathChanged(self, path_shown):
    "Called when path showing is toggled"
    if path_shown == QtCore.Qt.CheckState.Checked:
      self.show_paths = True
    else:
      self.show_paths = False
    
    # refresh
    self._updateMap()
    
  @QtCore.Slot()
  def _onPlaceSelectImages(self):
    "Place selected images in the centre of the current map view..."
    selected_image_id_list = self.photo_table.selected_image_id_list
    map_centre = self.view_data.map_settings.centre
    self._place_images(selected_image_id_list, map_centre.lng, map_centre.lat)
      
  def _place_images(self, image_id_list, longitude, latitude):
    "Put given images at positions"
    if len(image_id_list) != 0:
      self.db_manager.setPositionOnImages(image_id_list, longitude, latitude)
      #update photo table
      self._updatePhotoTable()
      #update web view
      self._updateMap()
      
  @QtCore.Slot()
  def _onZoomOutToAll(self):
    "Called when button to zoom out is called"
    #work out where the containing rectangle is...
    start_date = self.view_data.map_settings.map_start_date
    end_date = self.view_data.map_settings.map_end_date
    min_lat, max_lat, min_lng, max_lng = model.getLatLngRectContainingImagesBetween(self.db_manager.cursor, start_date, end_date)
    
    if None in [min_lat, max_lat, min_lng, max_lng]:
      self.displayError("No images have geographical data encoded in them.")
      return
    
    #expand by 5% 
    width = max_lat - min_lat
    height = max_lng - min_lng
    
    delta_w = 0.025 * width
    min_lat -= delta_w
    max_lat += delta_w
    
    delta_h = 0.025 * height
    min_lng -= delta_h
    max_lng += delta_h
    
    self._web_send("map.fitBounds([[%.6f, %.6f], [%.6f, %.6f]]);" % (min_lat, min_lng, max_lat, max_lng))

  @QtCore.Slot(int,int)
  def _onTimeSpanChanged(self, lower_percent, upper_percent):
    "Called when time slider changes"
    if self.slider_event_count == 0:
      QtCore.QTimer.singleShot(self.SLIDER_REFRESH_MS, self._updateTimeSpan)
    self.slider_event_count += 1
    
  def _updateTimeSpan(self):
    self.slider_event_count = 0
    lower_seconds = self._slider_time_to_seconds(self.time_slider.lower)
    upper_seconds = self._slider_time_to_seconds(self.time_slider.upper)
    #ensure rounding errors don't creep in on maximums
    if self.time_slider.upper == 100:
      upper_seconds += 1
    self.photo_table.first_index_after_date_filter = self.db_manager.getImageIndexAfterTimeTaken(lower_seconds)
    self.photo_table.last_index_after_date_filter = self.db_manager.getImageIndexAfterTimeTaken(upper_seconds)
    self.photo_table.repaintTable()
    #update the map
    self.view_data.map_settings.map_start_date = model.secondsToDate(lower_seconds)
    self.view_data.map_settings.map_end_date = model.secondsToDate(upper_seconds)
    self._updateMap()
    
  def run(self):
    "Run the application"
    self.main_window.show()
    # Enter Qt application main loop
   
  def _startScanTask(self, top_directory):
    "Kick off the scanner thread and connect to it's producer event"
    self.scanner_thread = exif.RecurseExifTask(top_directory)
    #connect thread safely
    self.scanner_thread.processedImgSignal.connect( self._onProcessedImgData, QtCore.Qt.QueuedConnection )
    self.scanner_thread.scanCompleteSignal.connect( self._onScanComplete, QtCore.Qt.QueuedConnection )
    
    self.accept_new_images = True
    #start thread
    self.scanner_thread.start()
    self._updateStatusBar()
    
  def _stopScanTask(self):
    "Stop any currently running scan task"
    if self.scanner_thread != None:
      #disconnect
      self.accept_new_images = False
      self.scanner_thread.processedImgSignal.disconnect( self._onProcessedImgData )
      #stop
      if self.scanner_thread.isRunning():
        self.scanner_thread.exit(-1)
        self.scanner_thread.wait( self._THREAD_WAIT_MS )
        self.view_data.current_image_set_info.end_scan_date = datetime.now()
        self.db_manager.saveViewData(self.view_data)
      #blank
      self.scanner_thread = None
      self._updateStatusBar()
  
  @QtCore.Slot()
  def _onScanComplete(self):
    #save the end time of the scan
    self.view_data.current_image_set_info.end_scan_date = datetime.now()
    self.db_manager.saveViewData(self.view_data)
    #update the status bar
    self._updateStatusBar()
    #check if we actually found any photos with geographical information
    imgs_with_geotags = model.getNumberOfImagesWithGeoTags(self.db_manager.cursor)
    if imgs_with_geotags == 0:
      qt_utils.show_warning_msg(self.main_window, "Scan complete. No photos containing geographical information found.", "Warning...")
    else:
      self._onZoomOutToAll()
      image_set_info = self.view_data.current_image_set_info
      qt_utils.show_msg(self.main_window, "Scan complete. Scanned %i images, %i with geotags found." % (image_set_info.number_of_images, imgs_with_geotags))
    
  @QtCore.Slot(str, dict)
  def _onProcessedImgData(self, image_file_path, image_data_map):
    "Process new image data"
    try:
      #bail if no longer accepting new items...
      if not self.accept_new_images:
        return
        
      #write new data to db but don't commit yet
      img_data = processedImgToImageData(image_file_path, image_data_map)
      self.db_manager.insertImage(img_data)
      
      #update min and max dates in the range...
      if img_data.taken_date != None:
        
        if self.view_data.current_image_set_info.number_of_images == 0 or\
           self.view_data.current_image_set_info.min_date > img_data.taken_date:
          self.view_data.current_image_set_info.min_date = img_data.taken_date
        
        if self.view_data.current_image_set_info.number_of_images == 0 or\
           self.view_data.current_image_set_info.max_date < img_data.taken_date:
          self.view_data.current_image_set_info.max_date = img_data.taken_date
      
      self.view_data.current_image_set_info.number_of_images += 1
       
      #mark view update required if not already
      if self.view_refresh_count == 0:
        ##SETUP QT timer to update GUI in refresh seconds...
        QtCore.QTimer.singleShot(self.VIEW_REFRESH_MS, self._updateGUIView)
      
      self.view_refresh_count += 1
      
    except Exception:
      self.displayError( "Exception processing image data" )
      traceback.print_exc()
  
  def _updateSliderRange(self):  
    self.main_window.right_side.time_labels.updateLabelPositions()
    
  @QtCore.Slot()
  def _updateGUIView(self):
    "Updates the view in the gui, using the current view settings..."
    try:
      #need to update the qt based image tables and sliders here....
      self.db_manager.cursor.connection.commit()  # make sure db is persisted....
      self._updatePhotoTable()
      self._updateSliderRange()
      self._updateMap()
      self._updateStatusBar()
      #reset refresh count
      self.view_refresh_count = 0
    except Exception:
      self.displayError("Exception updating view")
      traceback.print_exc()
    
  def _updateMap(self):
    #can't update map here as we can't know it's bounds, we will force the web view to institute a callback
    self._web_send("mapDataChanged();")
      
  def _updateStatusBar(self):
    "Update the status bar with what's going on"
    if self.main_window.isRunningScreenShown():
      image_set_info = self.view_data.current_image_set_info
      
      if (self.scanner_thread is not None and self.scanner_thread.isRunning()) or image_set_info.end_scan_date is None:
        status_text = "Scanning %s. Scan started at %s. %i images found." % (image_set_info.top_folder, 
                                                                             model.dateToDateTimeString(image_set_info.start_scan_date),
                                                                             image_set_info.number_of_images)
      else:
        status_text = "Scanned %s. Scan started at %s, ended at %s. %i images found." % (image_set_info.top_folder, 
                                                                                         model.dateToDateTimeString(image_set_info.start_scan_date),
                                                                                         model.dateToDateTimeString(image_set_info.end_scan_date),
                                                                                         image_set_info.number_of_images)
      
      self.main_window.statusLabel.setText(status_text)
    else:
      self.main_window.statusLabel.setText("")
      
  def _updatePhotoTable(self, buffered_range=None):
    "Update the images in the current photo table"
    self.photo_table.setTotalNumberOfImages(self.db_manager.getNumberOfImages())
    if buffered_range == None:
      buffered_range = self.photo_table.getDesiredBufferedImageRange()
    image_rows = self.db_manager.getImageSetAt(buffered_range[0], buffered_range[1] - buffered_range[0], True)
    self.main_window.photo_table.updatePhotos(buffered_range[0], image_rows)
    
  def _web_send(self, jscript):
    "Execute some javascript on the browser widget"
    self.main_window.webView.execute_script( jscript )
    
  def _getImageData(self, params):
    "Callback with all the details of an image in json format"
    callback_key = "callback"
    curried_key = "curried"
    image_id_key = "image_id"
    
    if params == None or callback_key not in params or not isinstance(params[callback_key], basestring) or len(params[callback_key]) == 0:
      self.displayError("Invalid call to getImageData")
      return
    
    if image_id_key not in params:
      self.displayError("Invalid call to getImageData")
      return
    
    if curried_key not in params:
      curried_obj = {}
    else:
      curried_obj = params[curried_key]
      
    callback = params[callback_key]
    
    try:
      image_id = int( params[image_id_key] )
    except ValueError:
      self.displayError("Invalid call to getImageData")
      return
    
    #overlay image with correct icon
    image_data = self.db_manager.getImageById(image_id)
    image_data.thumbnail = map_marker_logic.overlayImageDataWithIcon(image_data.thumbnail, 
                                                                     image_data.geo_type == model.ImageTable.GEO_FROM_USER)
  
    self._web_send("%s(%s, %s);" % (callback, json.dumps(curried_obj), json.dumps(image_data.serializeToDict())))

  def _imagesDragged(self, params):
    "Called when the user drags a draggable marker on the map"
    image_id_list_key = "image_id_list"
    longitude_key = "longitude"
    latitude_key = "latitude"
    
    if params is None or\
       image_id_list_key not in params or\
       longitude_key not in params or\
       latitude_key not in params:
      return
    
    image_id_list = params[image_id_list_key]
    latitude = params[latitude_key]
    longitude = params[longitude_key]
    
    self._place_images(image_id_list, longitude, latitude)
    
  def _mapPhotoHighlighted(self, params):
    "Called by the browser widget displaying the map when a photo is select on the map, using json encoding"
    image_id_key = "image_id"
    if params is None or image_id_key not in params:
      return
  
    image_id = params[image_id_key]
    image_index = self.db_manager.getImageIndexFromImageID(image_id)
    if image_index is not None:
      self.photo_table.scrollToIndex(image_index)
    
  def _mapMoved(self, params):
    "Called by the browser widget displaying the map, using json encoding"
    centre_lat_key = "centre-lat"
    centre_lng_key = "centre-lng"
    zoom_key = "zoom"
    north_key = "north"
    south_key = "south"
    west_key = "west"
    east_key = "east"
    map_width_key = "map_width"
    map_height_key = "map_height"
    
    if params == None or \
       centre_lat_key not in params or \
       centre_lng_key not in params or \
       zoom_key not in params or\
       north_key not in params or \
       south_key not in params or \
       west_key not in params or\
       east_key not in params or \
       map_width_key not in params or \
       map_height_key not in params:
      self.displayError("Invalid parameters to mapMoved")
      return
    
    centre = model.LatLng(params[centre_lat_key], params[centre_lng_key])
    zoom = params[zoom_key]
    
    #store new position
    if self.view_data.map_settings.zoom != zoom or \
       not model.areLatLngEqual( self.view_data.map_settings.centre, centre ):
      self.view_data.map_settings.centre = centre
      self.view_data.map_settings.zoom = zoom
    
      self.db_manager.setMapSettings(self.view_data.map_settings)
    
    #update non-table map-markers...
    self.updateMapMarkers([ params[south_key], params[north_key] ],
                          [ params[west_key], params[east_key] ],
                          params[map_width_key],
                          params[map_height_key])
  
  def updateMapMarkers(self, min_max_lat, min_max_lng, map_width_pixels, map_height_pixels):
    "Update the markers showing where images are..."
    # may want to take this of onto a worker thread for large data sets...
    map_lat_lng_rect = model.Rect(min_max_lat[0], min_max_lat[1], min_max_lng[0], min_max_lng[1])
    marker_logic_data = map_marker_logic.MarkerLogicData(self.db_manager.dbcon, 
                                                         self.view_data.map_settings, 
                                                         self.MAP_MARKER_IMG_WIDTH, 
                                                         self.MAP_MARKER_IMG_HEIGHT,
                                                         self.show_paths)
    merged_marker_list, arrow_list = map_marker_logic.updateMapMarkers(marker_logic_data, map_lat_lng_rect, map_width_pixels, map_height_pixels)
    
    
    new_idlatlng_list = []
    for x in merged_marker_list:
      new_idlatlng_list.extend(x.image_id_list)
      new_idlatlng_list.append(x.lat)
      new_idlatlng_list.append(x.lng)
  
    #only update map if something has changed
    if len(new_idlatlng_list) != len(self._last_idlatlng_list) or\
       len(arrow_list) != len(self._last_arrow_list) or \
       new_idlatlng_list != self._last_idlatlng_list or \
       arrow_list != self._last_arrow_list:
      #serialize and pass to gui
      s_merged_marker_list = [x.serializeToDict() for x in merged_marker_list]
      self._web_send("setMapMarkers(%s, %s);" % (json.dumps(s_merged_marker_list), json.dumps(arrow_list)))
      self._last_idlatlng_list = new_idlatlng_list
      self._last_arrow_list = arrow_list

    
def _map_contains(m, k):
  return k in m and m[k] != None and m[k] != ""


def processedImgToImageData(file_path, exif_map):
  "Convert the extracted image info into our data object"
  img_data = model.ImageData()
  img_data.geo_type = model.ImageTable.GEO_FROM_USER
  img_data.full_path = file_path
  
  if _map_contains(exif_map, exif.ParsedTags.DateTime) and \
     _map_contains(exif_map, exif.ParsedTags.DateTimeType):
    img_data.taken_date = exif_map[ exif.ParsedTags.DateTime ]
    img_data.taken_date_type = exif_map[ exif.ParsedTags.DateTimeType ]
  
  if _map_contains(exif_map, exif.ParsedTags.Make) and _map_contains(exif_map, exif.ParsedTags.Model):
    camera_make = exif_map[exif.ParsedTags.Make]
    camera_model = exif_map[exif.ParsedTags.Model]
    if camera_make not in camera_model:
      img_data.camera_make = camera_make + " " + camera_model
    else:
      img_data.camera_make = camera_model
  elif _map_contains(exif_map, exif.ParsedTags.Make):
    img_data.camera_make = exif_map[exif.ParsedTags.Make]
  elif _map_contains(exif_map, exif.ParsedTags.Model):
    img_data.camera_make = exif_map[exif.ParsedTags.Model]
  
  if _map_contains(exif_map, exif.ParsedTags.GPSInfo):
    img_data.latitude, img_data.longitude = exif_map[exif.ParsedTags.GPSInfo]
    img_data.geo_type = model.ImageTable.GEO_FROM_EXIF
   
  if _map_contains(exif_map, exif.ParsedTags.Thumbnail):
    img_data.thumbnail = exif_map[exif.ParsedTags.Thumbnail]

  return img_data
  
if __name__ == "__main__":
  from PySide.QtGui import QApplication
  app = QApplication(sys.argv)
  c = Controller()
  c.run()
  app.exec_()
  sys.exit()
