import model
import unittest
from PySide import QtGui, QtCore

WEB_IMG_FORMAT = "JPEG"


def overlayImageDataWithIcon(img_data, draggable):
  "Return a QImage with the correct icon overlay on it, from a binary str of jpeg data"
  #get a pixmap of the thumbnail 
  thumbnail_pixmap = model.imgdata_to_qpixmap(img_data, WEB_IMG_FORMAT)
  painter = QtGui.QPainter(thumbnail_pixmap)
  
  if draggable:
    overlay_icon = model.getPinImage()
  else:
    overlay_icon = model.getCompassImage()
    
  #paint on the overlay icon
  icon_src_rect = QtCore.QRect(0, 0, overlay_icon.width(), overlay_icon.height())
  icon_dest_rect = QtCore.QRect(0, 0, overlay_icon.width(), overlay_icon.height())
  painter.setOpacity(model.OVERLAY_ICON_OPACITY)
  painter.drawImage(icon_dest_rect, overlay_icon, icon_src_rect)
  painter.end()
  
  #now save back to jpeg data
  return model.qpixmap_to_imgdata(thumbnail_pixmap, WEB_IMG_FORMAT)

class MarkerLogicData(object):
  "Data required to work out where map markers are to be displayed"

  def __init__(self, db_connection, map_settings, map_marker_img_width, map_marker_img_height, calc_paths=False):
    """
    db_connection is a db_connection instance that is safe to use with a worker thread
    map_settings instance of MapSettings
    map_marker_img_width width of marker images in pixels
    map_marker_img_height height of marker images in pixels
    calc_paths compute paths between each photo group based on times

    Want this to be immutable for thread safety
    """
    self.db_connection = db_connection
    self.map_settings = map_settings
    self.map_marker_img_width = map_marker_img_width
    self.map_marker_img_height = map_marker_img_height
    self.max_images_per_marker = 10000
    self.calc_paths = calc_paths


def imageIDInMarkerList( test_id, marker_data_list ):
  "Return True if test_id is present in the marker_data_list"
  for marker_data in marker_data_list:
    if test_id in marker_data.image_id_list:
      return True
  # if we get here then it is not present
  return False

def updateMapMarkers(marker_logic_data, map_lat_lng_rect, map_width_pixels, map_height_pixels):
    """Workout the markers showing where images are...
    marker_logic_data is instance of MarkerLogicData
    map_lat_lng_rect  is the model.Rect object given the view port of the map in latitude and longitude
    map_width_pixels is the width of the map in pixels
    map_height_pixels is the height of the map in pixels
    Returns a list of model.MapMarkerData objects and an arrow_list  this is a list of tuples like ( (start_lng, start_lat), (end_lng, end_lat) )

    Want this to be able to run in worker thread safely
    """
    cursor = marker_logic_data.db_connection.cursor()

    try:
      #get smallest area of one marker on the map for which we will group pictures...
      marker_lat_delta = float(map_lat_lng_rect.width) / map_width_pixels * marker_logic_data.map_marker_img_width
      marker_lng_delta = float(map_lat_lng_rect.height) / map_height_pixels * marker_logic_data.map_marker_img_height
      
      marker_area = marker_lat_delta * marker_lng_delta
      
      #Given a marker return the lat/lng rect
      overlap_lat, overlap_lng = marker_lat_delta / 3, marker_lng_delta / 3 
      getMarkerRect = lambda marker: model.Rect(min_lat=marker.lat - overlap_lat, 
                                                max_lat=marker.lat + overlap_lat,
                                                min_lng=marker.lng - overlap_lng, 
                                                max_lng=marker.lng + overlap_lng)
        
      map_settings = marker_logic_data.map_settings
      
      map_start_date = map_settings.map_start_date
      map_end_date = map_settings.map_end_date
       
      #list of markers each marker defines x,y pos and list of image id's
      marker_data_list = []
      
      #do a quartering search to avoid too many queries or too many results
      #do quatering on a quantise completely covering rect to avoid to much variation
      #in grouping due to slight changes in start conditions
      quanta = max( map_lat_lng_rect.width, map_lat_lng_rect.height ) * 0.25
      search_list = model.quantiseRect(map_lat_lng_rect, quanta).generateQuarters()
      
      def processImagesInArea(map_start_date, map_end_date, test_rect, marker_data_list):
        image_id_list = model.getImagesIDsInArea(cursor, map_start_date, map_end_date, test_rect.min_lat, test_rect.max_lat, test_rect.min_lng, test_rect.max_lng, marker_logic_data.max_images_per_marker)
    
        #remove any images already present in other markers
        for image_id in image_id_list[:]:
          if imageIDInMarkerList(image_id, marker_data_list):
            image_id_list.remove(image_id)

        if len(image_id_list) != 0:
          #let's get an accurate average of position
          avg_pos = model.getAveragePositionOfImages(cursor, image_id_list)
          
          marker_data = model.MapMarkerData()
          marker_data.lat = avg_pos[0]
          marker_data.lng = avg_pos[1]
          marker_data.image_id_list = image_id_list
          marker_data.image_id_list.sort()
          marker_data_list.append(marker_data)
          
      while len(search_list) != 0:
        test_rect = search_list.pop(0)
        #if this is smaller than marker area then process it
        #otherwise see if we should quarter it again
        if test_rect.area > marker_area:
          #are there any images in this area?
          img_count = model.getImageCountInArea(cursor, map_start_date, map_end_date, test_rect.min_lat, test_rect.max_lat, test_rect.min_lng, test_rect.max_lng)

          if img_count > 1:
            search_list.extend(test_rect.generateQuarters())
          elif img_count == 1:
            processImagesInArea(map_start_date, map_end_date, test_rect, marker_data_list)
        else:
          processImagesInArea(map_start_date, map_end_date, test_rect, marker_data_list)
          
      #now go through the markers and see if any are close enough to be merged...
      marker_rect_list = [ (marker, getMarkerRect(marker)) for marker in marker_data_list ]
      
      # loop until we don't find any overlaps
      #force the first iteration to take place
      old_marker_count = len(marker_rect_list) + 1

      while len(marker_rect_list) != old_marker_count:
        old_marker_count = len(marker_rect_list)

        break_out = False

        for i in range(len(marker_rect_list) - 1):

          if break_out:
            break

          for j in range(i + 1, len(marker_rect_list)):
            marker_i, rect_i = marker_rect_list[i]
            marker_j, rect_j = marker_rect_list[j]

            if model.rectOverlap( rect_i, rect_j ):
              del marker_rect_list[i]  # remove i from marker_rect_list list
              if j < i:
                del marker_rect_list[j]  # remove j from marker_rect_list list
              else:
                del marker_rect_list[j - 1]
              merged_marker = model.mergeMapMarkerData(marker_i, marker_j)
              marker_rect_list.append( (merged_marker, getMarkerRect(merged_marker) ))
              break_out = True  # want to end this iteration and exit outside loop
              break  # exit this loop then the next
              
      #now should have a list of separated groups of map markers decorated with their covering area in marker_rect_list
      #go through and load up thumbnails we want to show
      #also work out if the marker is draggable
      for marker_data, _ in marker_rect_list:
        #want to convert this to a QImage and add overlay of pin or compass depending on whether the marker is
        #draggable or not
        #then convert back to jpeg for base64 serialization
         
        #work out if this marker is draggable
        #only draggable if all positions are set by the user
        geo_type_list = model.getGeoTypesFromImageList(cursor, marker_data.image_id_list)
        marker_data.draggable = False
        for geo_type in geo_type_list:
          marker_data.draggable = geo_type == model.ImageTable.GEO_FROM_USER
          if not marker_data.draggable:
            break
        
        #overlay img_data with correct icon
        marker_data.thumbnail = overlayImageDataWithIcon(model.getImageById(cursor, marker_data.image_id_list[0]).thumbnail, marker_data.draggable)
            
          
      #we can now look for min/max times in each group if we want
      arrow_list = [] # this is a list of tuples like ( (start_lng, start_lat), (end_lng, end_lat) ), of arrows to draw on the map
      if marker_logic_data.calc_paths and len(marker_rect_list) != 0:
        point_date_list = []
        #get min max times for each grouping
        for map_marker_data, _ in marker_rect_list:
          date_time_tuple = model.getMinMaxTimesFromImageList(cursor, map_marker_data.image_id_list)
          if date_time_tuple is not None:
            map_marker_data.min_taken_date, map_marker_data.max_taken_date = date_time_tuple
        
            #create lists of ([lng,lat], datetime), with one entry for min taken date and one for max taken date  
            #if more than one image in a group then there are likely min/max times associated with group
            #otherwise just the one time
            if len(map_marker_data.image_id_list) > 1 and map_marker_data.min_taken_date != map_marker_data.max_taken_date:
              point_date_list.append(([map_marker_data.lng, map_marker_data.lat], map_marker_data.min_taken_date) )
              point_date_list.append(([map_marker_data.lng, map_marker_data.lat], map_marker_data.max_taken_date) )
            elif len(map_marker_data.image_id_list) >= 1:
              point_date_list.append(([map_marker_data.lng, map_marker_data.lat], map_marker_data.min_taken_date) )
              
        #sort into date order.
        #iterate through choosing the earliest of each set for an arrow if [lng,lat]'s are different
        #also check for arrows travelling to or from outside this map area by running restricted searches on the db
        extract_seconds = lambda x: model.dateToSeconds(x[1])
        point_date_list.sort(key=extract_seconds) # sort into date order
        
        #go through an construct arrow list
        #look for photos earlier than the ones in the visible set to draw lines coming into this set
        if len(point_date_list) != 0:
          outside_point_date_list = model.getMinMaxTimesPhotosOutsideArea(cursor, map_lat_lng_rect.min_lat, map_lat_lng_rect.max_lat, map_lat_lng_rect.min_lng, map_lat_lng_rect.max_lng, map_start_date, point_date_list[0][1])
          if len(outside_point_date_list) != 0:
            arrow_list.append((outside_point_date_list[-1][0], point_date_list[0][0]))
        
        last_point_date = point_date_list[0]
        for point_date in point_date_list[1:]:
          #there may be an arrow between these 2 points going to the outside of the mapped zoom
          #need to find up to 2 photos outside this map area with min(date) or max(date) between these two times outside
          #this area 
          outside_point_date_list = model.getMinMaxTimesPhotosOutsideArea(cursor, map_lat_lng_rect.min_lat, map_lat_lng_rect.max_lat, map_lat_lng_rect.min_lng, map_lat_lng_rect.max_lng, last_point_date[1], point_date[1])
          
          if len(outside_point_date_list) == 0:
            if last_point_date[0] != point_date[0]:
              arrow_list.append( (last_point_date[0], point_date[0]) )
              
          elif len(outside_point_date_list) == 1:
            if last_point_date[0] != outside_point_date_list[0][0]:
              arrow_list.append( (last_point_date[0], outside_point_date_list[0][0]))
            if outside_point_date_list[0][0] != point_date[0]:
              arrow_list.append( (outside_point_date_list[0][0], point_date[0]) )
              
          elif len(outside_point_date_list) == 2:
            if last_point_date[0] != outside_point_date_list[0][0]:
              arrow_list.append( (last_point_date[0], outside_point_date_list[0][0]))
            if outside_point_date_list[1][0] != point_date[0]:
              arrow_list.append( (outside_point_date_list[1][0], point_date[0]) )
            
          
          last_point_date = point_date
          
        #look for photos later than the ones in the visible set to draw lines coming into this set
        if len(point_date_list) != 0:
          outside_point_date_list = model.getMinMaxTimesPhotosOutsideArea(cursor, map_lat_lng_rect.min_lat, map_lat_lng_rect.max_lat, map_lat_lng_rect.min_lng, map_lat_lng_rect.max_lng, point_date_list[-1][1], map_end_date)
          if len(outside_point_date_list) != 0:
            arrow_list.append((point_date_list[-1][0], outside_point_date_list[0][0]))
            
      #serialize to python primitives so we can convert to json
      merged_marker_list = [ x[0] for x in marker_rect_list ]
      #pass to gui
      return merged_marker_list, arrow_list
    finally:
      cursor.close()


class TestMarkerPositions(unittest.TestCase):

  def testLargeArea(self):
    test_db = "ext/test.db"
    db_manager = model.DBManager("0.1")
    db_manager.loadFile( test_db )

    map_settings = model.MapSettings()
    logic_data = MarkerLogicData(db_manager.dbcon, map_settings, 75, 75)
    map_lat_lng_rect = model.Rect(-15.28418, 72.81607, -64.6875, 93.86719)

    image_count = model.getImageCountInArea(db_manager.cursor, map_settings.map_start_date, map_settings.map_end_date, map_lat_lng_rect.min_lat, map_lat_lng_rect.max_lat, map_lat_lng_rect.min_lng, map_lat_lng_rect.max_lng)
    
    marker_list = updateMapMarkers(logic_data, map_lat_lng_rect, 600, 400)
    print image_count, len(marker_list)

    self.assertTrue( len(marker_list) <= image_count )


if __name__ == "__main__":
  unittest.main()
