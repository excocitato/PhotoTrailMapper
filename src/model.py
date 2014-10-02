import os
import sqlite3
import shutil
import file_utils
import unittest
from datetime import datetime, timedelta
import copy
import math
import base64
from PySide import QtCore, QtGui

epoch_start = datetime(1970, 1, 1)
month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

COMPASS_FILE = "images/compass.png"
PIN_FILE = "images/pin.png"

OVERLAY_ICON_OPACITY = 0.7

_compass_image = None
_pin_image = None

def getCompassImage():
  "Lazy load the compass image"
  global _compass_image
  if _compass_image is None:
    _compass_image = QtGui.QImage()
    _compass_image.load(COMPASS_FILE)
  return _compass_image

def getPinImage():
  "Lazy load the pin image"
  global _pin_image
  if _pin_image is None:
    _pin_image = QtGui.QImage()
    _pin_image.load(PIN_FILE)
  return _pin_image
  
class Consts(object):
  longitude_delta = 0.0001
  latitude_delta = 0.0001
  db_file_extension = "bxf"
  
  VERSION_MAJOR = 0
  VERSION_MINOR = 1

  
class Rect(object):

  def __init__(self, min_lat=0, max_lat=0, min_lng=0, max_lng=0):
    assert(min_lat <= max_lat)
    assert(min_lng <= max_lng)
    self.min_lat = min_lat
    self.max_lat = max_lat
    self.min_lng = min_lng
    self.max_lng = max_lng
    
  def __str__(self):
    return "lat %.5f to %.5f, lng %.5f to %.5f" % (self.min_lat, self.max_lat, self.min_lng, self.max_lng)
   
  @property
  def width(self):
    return self.max_lat - self.min_lat

  @property
  def height(self):
    return self.max_lng - self.min_lng
  
  @property
  def area(self):
    return self.height * self.width
  
  @property
  def centre(self):
    "return lat,lng for centre"
    return ((self.max_lat + self.min_lat) / 2, (self.max_lng + self.min_lng) / 2)

  def generateQuarters(self):
    "Divide the current rectangle into 4 quarter rectangles and return these in a list"
    w = self.width / 2
    h = self.height / 2
    return [Rect(self.min_lat, self.min_lat + w, self.min_lng, self.min_lng + h),
            Rect(self.min_lat + w, self.max_lat, self.min_lng, self.min_lng + h),
            Rect(self.min_lat, self.min_lat + w, self.min_lng + h, self.max_lng),
            Rect(self.min_lat + w, self.max_lat, self.min_lng + h, self.max_lng)]
    

def isWithin( x, interval ):
  "Return true if x is inclusively within interval"
  return x >= interval[0] and x <= interval[1]

  
def intervalOverlap( i1, i2 ):
  "Return true if the interval overlap (inclusively)"
  return isWithin( i1[0], i2) or \
      isWithin( i1[1], i2) or \
      isWithin( i2[0], i1) or \
      isWithin( i2[1], i1)


def rectOverlap( r1, r2 ):
  "Return true if r1 and r2 overlap"
  return intervalOverlap( (r1.min_lat, r1.max_lat), (r2.min_lat, r2.max_lat) ) and \
      intervalOverlap( (r1.min_lng, r1.max_lng), (r2.min_lng, r2.max_lng) )

def mergeRects( r1, r2 ):
  "Return the merger of the rectangle"
  merge = Rect(min(r1.min_lat, r2.min_lat), 
               max(r1.max_lat, r2.max_lat),
               min(r1.min_lng, r2.min_lng),
               max(r1.max_lng, r2.max_lng))
  return merge
  
def quantiseRect(r1, quanta=1):
  """Quantise a rect so that all co-ords are integer multiples of quanta AND
  the returned rect completely covers r1"""
  quantise_floor = lambda x: math.floor(x/quanta) * quanta
  quantise_ceil = lambda x: math.ceil(x/quanta) * quanta
  return Rect( quantise_floor(r1.min_lat), 
               quantise_ceil(r1.max_lat),
               quantise_floor(r1.min_lng),
               quantise_ceil(r1.max_lng))
 
def generateLatLongRect(longitude, latitude):
  return (longitude - Consts.longitude_delta, longitude + Consts.longitude_delta,
          latitude - Consts.latitude_delta, latitude + Consts.latitude_delta)
    

def secondsToDate(seconds):
  "Convert seconds from 1st Jan 1970 to a datetime object"
  if seconds != None:
    return epoch_start + timedelta(seconds=seconds)
  else:
    return None


def dateToDateTimeString(d):
  "return formated string representing the date"
  return "{0:d} {1:s} {2:d} {3:#02d}:{4:#02d}:{5:#02d}".format(d.day, month_names[d.month - 1], d.year, d.hour, d.minute, d.second)


def dateToDateString(d):
  "Return formatted string representing calendar date"
  return "{0:d} {1:s} {2:d}".format(d.day, month_names[d.month - 1], d.year)


def secondsToDateTimeString(seconds):
  "Convert from seconds from 1st Jan 1970 to a human date time string"
  if seconds != None:
    return dateToDateTimeString(secondsToDate(seconds))
  else:
    return ""


def secondsToDateString(seconds):
  if seconds != None:
    return dateToDateString(secondsToDate(seconds))
  else:
    return ""

    
def dateToSeconds(_date):
  "Convert a date into seconds from 1st Jan 1970"
  if _date != None:
    return (_date - epoch_start).total_seconds()
  else:
    return None

class ScannedImageSet(object):
  "Represents Overall details of a set of scanned images..."
  
  def __init__(self):
    self.top_folder = ""
    self.start_scan_date = datetime.now()
    self.end_scan_date = None #may be null if the scan has not finished 
    self.number_of_images = 0
    #init min/max this way round so inequalities work when updating...
    self.min_date = datetime.now()
    self.max_date = copy.deepcopy(epoch_start)
    self.db_file = ""
  
class ImageData(object):
  "Complete data for one image"
  
  def __init__(self):
    self.image_id = None
    self.latitude = None #may not have geographic data
    self.longitude = None #may not have geographic data
    self.geo_type = None  #the type may come from EXIF info or be user specified
    self.camera_make = ""
    self._full_path = ""
    self.filename = ""
    self.taken_date = None #may not have a date, otherwise a datetime object
    self.taken_date_type = None
    self.thumbnail = "" #binary string encoded jpeg binary data

  def getFullPath(self):
    return self._full_path
  
  def setFullPath(self,x):
    self._full_path = x
    self.filename = file_utils.getFilenameFromPath(x)
  
  full_path = property(getFullPath,setFullPath)
  
  def serializeToDict(self):
    "This is the first step to transferring this to web view"
    d = {}
    seriliaze_attrs = ["image_id", "latitude", "longitude", "camera_make", "filename", "full_path",
                       "taken_date_type", "geo_type"]
    for attr in seriliaze_attrs:
      d[attr] = getattr(self, attr)
    d["taken_date"] = dateToSeconds(self.taken_date)
    d["thumbnail"] = base64.b64encode(self.thumbnail)
    return d
      
class LatLng(object):
  
  def __init__(self, lat=0, lng=0):
    self.lat = lat
    self.lng = lng
    
def areLatLngEqual(latlng1, latlng2):
  dp = 3
  return round(latlng1.lat, dp) == round(latlng2.lat, dp) and round(latlng1.lng, dp) == round(latlng2.lng, dp)

class MapSettings(object):
  "represent map bounds"
  
  def __init__(self, centre=None, zoom=None, map_start_date=None, map_end_date=None):
    self.map_pos_locked = False #don't change the map location as time selection is altered
    if map_start_date is None:
      self.map_start_date = copy.deepcopy(epoch_start) #datetime
    else:
      self.map_start_date = map_start_date
      
    if map_end_date is None:
      self.map_end_date = datetime.now() #datetime
    else:
      self.map_end_date = map_end_date
    
    if centre != None:
      self.centre = centre
    else:
      self.centre = LatLng()
    if zoom != None:
      self.zoom = zoom
    else:
      self.zoom = 1

class ViewData(object):
  "Represents the top level of data for the app run time and persistent data"

  def __init__(self):
    self.current_image_set_info = ScannedImageSet()
    self.map_settings = MapSettings([0,0], 8)
      
class MapMarkerData(object):
  "Represents the data under one map marker"
  
  def __init__(self):
    self.lat = 0
    self.lng = 0
    self.image_id_list = []
    self.thumbnail = "" #if this is a merged marker it is the first thumbnail in the list
    self.min_taken_date = datetime.now()
    self.max_taken_date = datetime.now()
    self.draggable = False  # is this marker draggable
    
  def serializeToDict(self):
    "Starting point of transferring this over to the javascript map"
    d = {}
    seriliaze_attrs = ["lat", "lng", "image_id_list", "draggable"]
    for attr in seriliaze_attrs:
      d[attr] = getattr(self, attr)
      
    d["min_taken_date"] = dateToSeconds(self.min_taken_date)
    d["max_taken_date"] = dateToSeconds(self.max_taken_date)
    
    #now sort out the thumbnail as base_64 encoding
    d["thumbnail"] = base64.b64encode( self.thumbnail )
    return d
    
def mergeMapMarkerData(marker1, marker2):
  "Combine 2 markers into 1 marker"
  combined = MapMarkerData()
  combined.lat = ( marker1.lat * len(marker1.image_id_list) + marker2.lat * len(marker2.image_id_list) ) / (len(marker1.image_id_list) + len(marker2.image_id_list))
  combined.lng = ( marker1.lng * len(marker1.image_id_list) + marker2.lng * len(marker2.image_id_list) ) / (len(marker1.image_id_list) + len(marker2.image_id_list))
  combined.image_id_list.extend(marker1.image_id_list)
  combined.image_id_list.extend(marker2.image_id_list)
  combined.image_id_list.sort()
  combined.thumbnail = marker1.thumbnail
  return combined

def distanceBetweenMarkers(marker1, marker2):
  "Return approx distance between markers"
  lat_delta = marker1.lat - marker2.lat
  lng_delta = marker1.lng - marker2.lng
  return math.sqrt(lat_delta*lat_delta + lng_delta*lng_delta)

class ImageTable(object):
  _columns = [("image_id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
              ("file", "TEXT"),
              ("camera_make", "TEXT"),
              ("taken_date", "INTEGER"),
              ("taken_date_type", "INTEGER"),
              ("longitude", "REAL"),
              ("latitude", "REAL"),
              ("geo_type", "INTEGER"),
              ("thumbnail", "BLOB")]  # blob of jpg binary data
  
  #indexs are defines in DB manager
  schema = """CREATE TABLE Image(%s);""" % (",".join(["%s %s" % (x, y) for x, y in _columns]))

  taken_date_types = (TAKEN_DATE_FROM_EXIF, DATE_FROM_FILE) = range(0, 2)
  geo_types = (GEO_FROM_EXIF, GEO_FROM_USER) = range(0, 2)

  
def getImagesIDsInArea(cursor, map_start_date, map_end_date, min_lat, max_lat, min_lng, max_lng, limit=None):
    "return a list of [image id's] in the area"
    map_start_date = dateToSeconds(map_start_date)
    map_end_date = dateToSeconds(map_end_date)
    
    if limit != None:
      limit_sql = " LIMIT %i" % limit
    else:
      limit_sql = ""
      
    sql = """SELECT Image.image_id, longitude, latitude from Image,ImageLocation
    WHERE Image.image_id == ImageLocation.image_id AND
    taken_date >= ? AND
    taken_date <= ? AND
    max_longitude >= ? AND
    min_longitude <= ? AND
    max_latitude >= ? AND
    min_latitude <= ?%s;""" % limit_sql
    cursor.execute( sql, (map_start_date, map_end_date, min_lng, max_lng, min_lat, max_lat) )
    return [row[0] for row in cursor.fetchall() if row[1] >= min_lng and row[1] <= max_lng and
                                                   row[2] >= min_lat and row[2] <= max_lat ]

def getAveragePositionOfImages(cursor, image_id_list):
  "Return the average lat,lng of images in the image_id_list"
  sql="SELECT AVG(latitude), AVG(longitude) FROM Image WHERE image_id IN ({seq})".format(seq=','.join(['?'] * len(image_id_list)))
  cursor.execute(sql, image_id_list)
  return cursor.fetchone()

def getGeoTypesFromImageList(cursor, image_id_list):
  "Return the of geo types for the given image_id list"
  sql = "SELECT geo_type FROM Image WHERE image_id IN({seq})".format(seq=','.join(['?'] * len(image_id_list )))
  cursor.execute(sql, image_id_list)
  return [x[0] for x in cursor.fetchall()]

def getMinMaxTimesFromImageList(cursor, image_id_list):
  "Return the tuple of (min date_taken, max date_taken) for photos in the given area or None if no photos exist"
  if len(image_id_list) == 0:
    return None
  else:
    sql = "SELECT MIN(taken_date), MAX(taken_date) from Image WHERE image_id in ({seq})".format(seq=','.join(['?'] * len(image_id_list)))
    cursor.execute(sql, image_id_list)
    row = cursor.fetchone()
    if row is not None and len(row) == 2:
      return (secondsToDate(row[0]), secondsToDate(row[1]))
    else:
      return None
  
def getMinMaxTimesFromImagesInArea(cursor, min_lat, max_lat, min_lng, max_lng):
  "Return the tuple of (min date_taken, max date_taken) for photos in the given area or None if no photos exist"
  sql = """SELECT MIN(taken_date), MAX(taken_date) from Image,ImageLocation
  WHERE Image.image_id == ImageLocation.image_id AND
  Image.longitude >= ? AND
  Image.longitude <= ? AND
  Image.latitude >= ? AND
  Image.latitude <= ? AND
  max_longitude >= ? AND
  min_longitude <= ? AND
  max_latitude >= ? AND
  min_latitude <= ?;"""
  cursor.execute(sql, (min_lng, max_lng, min_lat, max_lat, min_lng, max_lng, min_lat, max_lat))
  row = cursor.fetchone()
  if row is not None and len(row) == 2:
    return (secondsToDate(row[0]), secondsToDate(row[1]))
  else:
    return None

def getMinMaxTimesPhotosOutsideArea(cursor, min_lat, max_lat, min_lng, max_lng, min_date, max_date):
  """Return ([lng,lat], datetime) for photos outside the area described by min/max lat/lngs 
  with taken times between the limits min_date, max_date, but only
  for max,min times in this set"""
  match_list = []
  min_seconds = dateToSeconds(min_date)
  max_seconds = dateToSeconds(max_date)
  #divide search region into 4 rects that exclude the target rect
  #1 region Image.longitude < min_lng
  #2 region Image.longitude > max_lng
  #3 region Image.longitude >= min_lng AND Image.longitude <= max_lng AND Image.latitude < min_lat
  #4 region Image.longitude >= min_lng AND Image.longitude <= max_lng AND Image.latitude > max_lat
  sql_min = """SELECT Image.longitude, Image.latitude, taken_date, Image.image_id  from Image,ImageLocation
  WHERE Image.image_id == ImageLocation.image_id AND
  ( Image.longitude < ? OR
    Image.longitude > ? OR
    (Image.longitude >= ? AND Image.longitude <= ? AND Image.latitude < ? ) OR
    (Image.longitude >= ? AND Image.longitude <= ? AND Image.latitude > ? ) ) AND
  taken_date >= ? AND taken_date < ?
  ORDER BY taken_date ASC LIMIT 1;"""
  cursor.execute(sql_min, (min_lng, max_lng, min_lng, max_lng, min_lat, min_lng, max_lng, max_lat, min_seconds, max_seconds))
  row = cursor.fetchone()
  min_id = None
  if row is not None and len(row) == 4:
    min_id = row[3]
    match_list.append( ([row[0], row[1]], secondsToDate(row[2])))
  
  sql_max = """SELECT Image.longitude, Image.latitude, taken_date, Image.image_id  from Image,ImageLocation
  WHERE Image.image_id == ImageLocation.image_id AND
  ( Image.longitude < ? OR
    Image.longitude > ? OR
    (Image.longitude >= ? AND Image.longitude <= ? AND Image.latitude < ? ) OR
    (Image.longitude >= ? AND Image.longitude <= ? AND Image.latitude > ? ) ) AND
  taken_date > ? AND taken_date <= ?
  ORDER BY taken_date DESC LIMIT 1;"""
  cursor.execute(sql_max, (min_lng, max_lng, min_lng, max_lng, min_lat, min_lng, max_lng, max_lat, min_seconds, max_seconds))
  row = cursor.fetchone()
  if row is not None and len(row) == 4 and min_id != row[3]: # don't add the same record twice for min/max
    match_list.append( ([row[0], row[1]], secondsToDate(row[2])))
  
  return match_list
  
def getLatLngRectContainingAllImages(cursor):
  "Return (min lat, max lat, min lng, max lng) rectangle that contains all the images"
  sql = "SELECT MIN(latitude), MAX(latitude), MIN(longitude), MAX(longitude) FROM Image;"
  cursor.execute(sql)
  return cursor.fetchone()

def getLatLngRectContainingImagesBetween(cursor, start_date, end_date):
  sql = "SELECT MIN(latitude), MAX(latitude), MIN(longitude), MAX(longitude) FROM Image WHERE taken_date >= ? AND taken_date <= ?;"
  cursor.execute(sql, (dateToSeconds(start_date), dateToSeconds(end_date)))
  return cursor.fetchone()

def getImageById(cursor, image_id):
    "Return an ImageData object from a given image_id or None if it does not exist"
    sql = "SELECT file,camera_make,taken_date,taken_date_type,longitude,latitude,geo_type,thumbnail FROM Image WHERE image_id=?;"
    cursor.execute(sql, (image_id,))
    row = cursor.fetchone()
    if row != None:
      image_data = ImageData()
      image_data.image_id = image_id
      image_data.full_path = row[0]
      image_data.camera_make = row[1]
      image_data.taken_date = secondsToDate(row[2])
      image_data.taken_date_type = row[3]
      image_data.longitude = row[4]
      image_data.latitude = row[5]
      image_data.geo_type = row[6]
      image_data.thumbnail = row[7]
      return image_data
    else:
      return None


def getImageCountInArea(cursor, map_start_date, map_end_date, min_lat, max_lat, min_lng, max_lng):
    map_start_date = dateToSeconds(map_start_date)
    map_end_date = dateToSeconds(map_end_date)
    #get overlaps
    sql = """SELECT COUNT(Image.image_id) from Image,ImageLocation
    WHERE Image.image_id == ImageLocation.image_id AND
    taken_date >= ? AND
    taken_date <= ? AND
    max_longitude >= ? AND
    min_longitude <= ? AND
    max_latitude >= ? AND
    min_latitude <= ?;"""
    cursor.execute(sql, (map_start_date, map_end_date, min_lng, max_lng, min_lat, max_lat))
    return cursor.fetchone()[0]
    
def getNumberOfImagesWithGeoTags(cursor):
  "Get the number of images that actually had geographical information in them"
  #CREATE VIRTUAL TABLE ImageLocation USING rtree(image_id
  sql = "SELECT COUNT(image_id) FROM ImageLocation;"
  cursor.execute(sql)
  return cursor.fetchone()[0]
  
def getMapSettings(cursor):
  "Get the map view port if any"
  #MapSettings(centre_latitude REAL, centre_longitude REAL, zoom INT, map_start_date INT, map_end_date INT);
  sql = "SELECT centre_latitude, centre_longitude, zoom, map_start_date, map_end_date FROM MapSettings;"
  cursor.execute(sql)
  row = cursor.fetchone()
  if row != None and len(row) == 5:
    return MapSettings(LatLng(row[0], row[1]), row[2], secondsToDate(row[3]), secondsToDate(row[4]))
  else:
    return MapSettings()
  
def setMapSettings(cursor, map_settings):
  cursor.execute("DELETE FROM MapSettings;")
  sql = "INSERT INTO MapSettings(centre_latitude, centre_longitude, zoom, map_start_date, map_end_date) VALUES(?,?,?,?,?);"
  cursor.execute(sql, (map_settings.centre.lat, 
                       map_settings.centre.lng, 
                       map_settings.zoom, 
                       dateToSeconds(map_settings.map_start_date),
                       dateToSeconds(map_settings.map_end_date)))
  cursor.connection.commit()
  
class CSVColumn(object):
  def __init__(self, header_name, row_index, to_str=str):
    self.header_name = header_name
    self.row_index = row_index
    self.to_str = to_str
    
def exportImageDataToCSV(cursor, target_file):
  "Export the image data to a csv file, may throw a runtime error if fails"
  # ("file", "TEXT"),("camera_make", "TEXT"), ("taken_date", "INTEGER"), ("taken_date_type", "INTEGER"),
  # "longitude", "REAL"), ("latitude", "REAL"),("thumbnail", "BLOB")]
  
  def quote_str(x):
    return '"%s"' % x
  
  def date_type_to_str(x):
    if x == ImageTable.TAKEN_DATE_FROM_EXIF:
      return quote_str("Date Taken By Camera")
    else:
      return quote_str("File Creation Date")    

  def geo_type_to_str(x):
    if x == ImageTable.GEO_FROM_EXIF:
      return quote_str("GPS from EXIF data in photo")
    else:
      return quote_str("Position supplied by user")
    
  csv_column_list = [CSVColumn("File", 0, quote_str), 
                     CSVColumn("Camera Make", 1, quote_str), 
                     CSVColumn("Date", 2, lambda x: quote_str(secondsToDateTimeString(x))),
                     CSVColumn("Date Type", 3, date_type_to_str),
                     CSVColumn("Latitude", 5),
                     CSVColumn("Longitude", 6),
                     CSVColumn("Position Data Source", 4, geo_type_to_str)]
  
  sql = "SELECT file, camera_make, taken_date, taken_date_type, geo_type, latitude, longitude from Image;"
  f = open(target_file, 'w')
  try:
    #write out header row
    f.write(",".join([quote_str(x.header_name) for x in csv_column_list]) + "\n")
    cursor.execute(sql)
    row = cursor.fetchone()
    while row is not None and len(row) != 0:
      csv_row = []
      for cvs_col in csv_column_list:
        csv_row.append( cvs_col.to_str( row[ cvs_col.row_index ] ) )
      f.write( ",".join(csv_row) + "\n")
      row = cursor.fetchone()
  
  finally:
    f.close()
    
  
class DBManager(object):
  "Class that looks after our working database..."

  #date stored in seconds since Midnight 1 Jan 1970
  schema = ["CREATE TABLE AppInfo (app_version TEXT, db_version INT);",
            "CREATE TABLE ScanInfo (top_folder TEXT, start_scan_date INT, end_scan_date INT);",
            ImageTable.schema,
            "CREATE INDEX image_date_index ON Image(taken_date);",
            "CREATE VIRTUAL TABLE ImageLocation USING rtree(image_id, min_longitude, max_longitude, min_latitude, max_latitude);",
            "CREATE TABLE MapSettings(centre_latitude REAL, centre_longitude REAL, zoom INT, map_start_date INT, map_end_date INT);"]
  
  version_updates_map = {}  # map of version updates, key is version to go to, value is script to run
   
  current_db_version = 1
  
  def __init__(self, app_version):
    self.db_file = ""
    self.saved_to_file = ""  # file that this data was loaded from or last saved to
    self.app_version = app_version
    self.version = 1
    self.dbcon = None
    self.cursor = None
    self._dirty = False # is there date that is not save permently
    self.db_version = DBManager.current_db_version
    
  def getDirty(self):
    return self._dirty
  
  def setDirty(self, x):
    self._dirty = x
    
  dirty = property(getDirty, setDirty)
  
  def _setAppInfo(self, dbversion=None):
    if dbversion == None:
      dbversion = self.db_version
    setsql = """DELETE FROM AppInfo;
    INSERT INTO AppInfo(app_version, db_version) VALUES("%s",%f);""" % ( self.app_version, self.db_version)
    self.cursor.executescript( setsql )
    self.cursor.connection.commit()

  def _getCurrentDBVersion(self):
    sql = "SELECT db_version FROM AppInfo;"
    self.cursor.execute(sql)
    return self.cursor.fetchone()[0]
    
  def _runschema(self):
    "Run the schema over the database, should only be done for new/blank dbs"
    self.cursor.executescript( "".join(self.schema) )
    self.cursor.connection.commit()
    #set version info
    self._setAppInfo()

  def _checkUpgrade(self):
    "For the future"
    loaded_version = self._getCurrentDBVersion()
    if loaded_version != 1:
      raise RuntimeError("Unknown database version.")
  
  def _connect(self, db_file):
    "Connect to a given database, raises an exception on error"
    assert( self.dbcon == None ) #don't do this twice without disconnecting
    #test if database exists
    self.db_file = db_file
    exists = os.path.exists(db_file)
    #_connect, which creates it if it doesn't
    self.dbcon = sqlite3.connect(db_file)
    self.cursor = self.dbcon.cursor()
    if not exists:
      #this is clean so lets create some tables etc
      self._runschema()
    else:
      self._checkUpgrade()

  def _disconnect(self):
    "Disconnect from a given database"
    if self.dbcon != None:
      self.dbcon.close()
      self.cursor  = None
      self.dbcon = None
      
  def _disconnectAndClean(self):
    "Disconnect from our temp database file and remove it"
    old_temp = self.db_file
    self._disconnect()
    self.saved_to_file = ""
    #delete previous temp file if any
    if os.path.exists(old_temp):
      os.remove(old_temp)
      
  @classmethod
  def _createTempDBFile(cls):
    return file_utils.createOpenedTempNamedFile()
  
  def isConnected(self):
    return self.dbcon != None
  
  def close(self):
    "Call to close disconnecet and clean"
  
    self._disconnectAndClean()
    
  def loadFile(self, load_file_name):
    """Load a saved file. This will copy the database to a temporary file then _connect to that.
    Raises an exception on failure"""
    if not os.path.exists(load_file_name):
      raise RuntimeError("File does not exist! %s" % load_file_name)
    
    self._disconnectAndClean()
    
    #create a new temp...
    tmp_file = self._createTempDBFile()
    try:
      #now stream in chunks of up to 1Mb
      chunk_size = 1024 * 1024
      #open load file read only
      with open(load_file_name,'rb') as load_file:
        while True:
          chunk_block = load_file.read(chunk_size)
          if chunk_block == None or chunk_block == "":
            break
          tmp_file.write( chunk_block )
      #once copied close and _connect
      tmp_file.close()
      self._connect(tmp_file.name)
      self.saved_to_file = load_file_name
      self.dirty = False
    except:
      #try and untangle our state from the failure!
      try:
        self._disconnect()
      except:
        pass
      try:
        if not tmp_file.closed():
          tmp_file.close()
      except:
        pass
      #make sure temp file removed on error
      os.remove(tmp_file.name)
      raise  # pass error up
         
  def saveFile(self, save_file):
    """Save the current temporary database to the specified file overwriting as required.
    Raises an exception on failure"""
    if self.db_file == "":
      raise RuntimeError("No database to save!")
    #rem the file name
    cur_file = self.db_file
    self.dbcon.commit()
    self._disconnect()
    try:
      shutil.copy(cur_file, save_file)
      self.saved_to_file = save_file
      self.dirty = False
    finally:
      #reconnect
      self._connect(cur_file)
      
  def newFile(self):
    """Create a new file for our purposes
    May raise an exception if it fails..."""
    self._disconnectAndClean()
    tmp_file = self._createTempDBFile()
    #close this file but use it's name
    tmp_file.close()
    tmp_name = tmp_file.name
    os.remove(tmp_name)
    self._connect(tmp_name)
    self.dirty = False
    
  def getNumberOfImages(self):
    if not self.isConnected():
      return 0
    sql = "SELECT COUNT(image_id) FROM Image;"
    self.cursor.execute(sql)
    return self.cursor.fetchone()[0]
    
  def getMinMaxDate(self):
    "Return the min/max date"
    if not self.isConnected():
      raise RuntimeError("Not connected!")
    
    sql = "SELECT MIN(taken_date),MAX(taken_date) from Image;"
    self.cursor.execute(sql)
    row = self.cursor.fetchone()
    if row == None or len(row) != 2 or row[0] == None or row[1] == None:
      return epoch_start, epoch_start
    
    min_seconds, max_seconds = row[0], row[1]
    return secondsToDate(min_seconds), secondsToDate(max_seconds)
  
  def getTopFolderAndScanDates(self):
    "Return the (scan_folder, start_date, end_date), end_date may be None"
    #"ScanInfo (top_folder TEXT, start_scan_date INT, end_scan_date INT);"
    if not self.isConnected():
      return "", epoch_start, None
    
    sql = "SELECT top_folder, start_scan_date, end_scan_date FROM ScanInfo;";
    self.cursor.execute(sql)
    row = self.cursor.fetchone()
    if row == None or row[0] == None or row[1] == None:
      return "", epoch_start, None
    
    return row[0], secondsToDate(row[1]), secondsToDate(row[2])
    
  def setTopFolderAndScanDate(self, top_folder, start_scan_date):
    "set the top folder and scan date"
    if not self.isConnected():
      raise RuntimeError("No database connection!")
    
    sql = "INSERT OR REPLACE INTO ScanInfo(top_folder,start_scan_date) VALUES(?,?);"
    self.cursor.execute(sql,(top_folder,dateToSeconds(start_scan_date)))
    self.dbcon.commit()
    self.dirty = True
    
  def setEndScanDate(self, end_scan_date):
    if not self.isConnected():
      raise RuntimeError("No database connection!")
    
    sql = "INSERT OR REPLACE INTO ScanInfo(end_scan_date) VALUES(?);"
    self.cursor.execute(sql, (dateToSeconds(end_scan_date),) )
    self.cursor.connection.commit()
    self.dirty = True
  
  def getScannedImageSet(self):
    "Returns info about the contained set"
    scannedSet = ScannedImageSet()
    scannedSet.top_folder, scannedSet.start_scan_date, scannedSet.end_scan_date = self.getTopFolderAndScanDates()
    scannedSet.number_of_images = self.getNumberOfImages()
    scannedSet.min_date, scannedSet.max_date = self.getMinMaxDate()
    scannedSet.db_file = self.saved_to_file
    return scannedSet

  def getViewData(self):
    "Load the view data settings"
    view_data = ViewData()
    view_data.current_image_set_info = self.getScannedImageSet()
    view_data.map_settings = getMapSettings(self.cursor)
    return view_data  
    
  def saveViewData(self, view_data):
    self.setTopFolderAndScanDate(view_data.current_image_set_info.top_folder, view_data.current_image_set_info.start_scan_date)
    self.setEndScanDate(view_data.current_image_set_info.end_scan_date)
    setMapSettings(self.cursor, view_data.map_settings)
    self.dirty = True
      
  def getImageById(self, image_id):
    "Return an ImageData object from a given image_id or None if it does not exist"
    return getImageById(self.cursor, image_id)
    
  def insertImage(self, image_data):
    """Insert an image into the database, return the same object with image_id filled in
    It does not call commit though!
    """
    if image_data.image_id != None:
      raise RuntimeError("Image already in database!")
    
    sql = "INSERT INTO Image(file,camera_make,taken_date,taken_date_type,longitude,latitude,geo_type,thumbnail) VALUES(?,?,?,?,?,?,?,?);"
    
    self.cursor.execute(sql, (image_data.full_path,
                              image_data.camera_make,
                              dateToSeconds(image_data.taken_date),
                              image_data.taken_date_type,
                              image_data.longitude,
                              image_data.latitude,
                              image_data.geo_type,
                              buffer(image_data.thumbnail)))
    image_data.image_id = self.cursor.lastrowid
    
    if image_data.latitude != None and image_data.longitude != None:
      #(image_id, min_longitude, max_longitude, min_latitude, max_latitude
      min_longitude,max_longitude,min_latitude,max_latitude = generateLatLongRect(image_data.longitude, image_data.latitude)
      sql = "INSERT INTO ImageLocation(image_id,min_longitude,max_longitude,min_latitude,max_latitude) VALUES(?,?,?,?,?);"
      self.cursor.execute(sql,(image_data.image_id,min_longitude,max_longitude,min_latitude,max_latitude))
    
    self.dirty = True
    
    return image_data
        
  def setPositionOnImages(self, image_id_list, longitude, latitude):
    "Set user specified position on the give images"
    sql = "UPDATE Image SET longitude=?, latitude=?, geo_type=? WHERE image_id IN ({seq});".format(seq=','.join(['?'] * len(image_id_list)))
    sql_args = [longitude, latitude, ImageTable.GEO_FROM_USER]
    sql_args.extend(image_id_list)
    
    self.cursor.execute(sql, sql_args)

    #now update r-tree table  
    min_longitude,max_longitude,min_latitude,max_latitude = generateLatLongRect(longitude, latitude)
    
    sql = "INSERT OR REPLACE INTO ImageLocation(image_id,min_longitude,max_longitude,min_latitude,max_latitude) VALUES(?,?,?,?,?);"
    for image_id in image_id_list:
      self.cursor.execute(sql,(image_id, min_longitude ,max_longitude, min_latitude, max_latitude))

    self.dbcon.commit()
    
    self.dirty = True
    
  def getMapSettings(self):
    "Get the map view port if any"
    return getMapSettings(self.cursor)
    
  def setMapSettings(self, map_settings):
    setMapSettings(self.cursor, map_settings)
    self.dirty = True
  
  def getImageCountInArea(self, map_start_date, map_end_date, min_lat, max_lat, min_lng, max_lng):
    return getImageCountInArea(self.cursor, map_start_date, map_end_date, min_lat, max_lat, min_lng, max_lng)

  def getImagesIDsInArea(self, map_start_date, map_end_date, min_lat, max_lat, min_lng, max_lng, limit=None):
    "return a list of [image id's] in the area"
    return getImagesIDsInArea(self.cursor, map_start_date, map_end_date, min_lat, max_lat, min_lng, max_lng, limit)
  
  def getAveragePositionOfImages(self, image_id_list):
    "Return the average lat,lng of images in the image_id_list"
    return getAveragePositionOfImages(self.cursor, image_id_list)
    
  def getImageLocationById(self, image_id):
    """Return a row of latitude,longitude or None"""
    sql = "SELECT latitude, longitude FROM Image WHERE image_id=?;"
    self.cursor.execute(sql, (image_id,))
    return self.cursor.fetchone()
  
  def getImageIndexAfterTimeTaken(self, time_taken_seconds):
    """Image Index is the position in the date ordered array of images (not the image id)
    This is a little unpleasant May need to review this for speed
    Returns None if there is None"""
    sql_cmd = """SELECT COUNT(image_id) from Image WHERE taken_date < ? ORDER BY taken_date;"""
    self.cursor.execute(sql_cmd, (time_taken_seconds,))
    row = self.cursor.fetchone()
    return row[0] 
  
  def getImageIndexFromImageID(self, image_id):
    """Given an image id find it's image index, that is position in the time sorted list of images
    returns None if there is none"""
    image_data = self.getImageById(image_id)
    if image_data is None:
      return None
    
    return self.getImageIndexAfterTimeTaken( dateToSeconds(image_data.taken_date) - 1 )
    
  def getImageSetAt(self, start_index, number_of_images, ascending):
    """Return the specified set of images, useful for scrolling"""
    if ascending:
      asc_desc = "ASC"
    else:
      asc_desc = "DESC"
  
    sort_by_sql = "ORDER BY taken_date %s" % (asc_desc)
    args = (number_of_images, start_index)
    sql_cmd = """SELECT image_id, file, camera_make, taken_date, taken_date_type, longitude, latitude, geo_type, thumbnail from Image %s LIMIT ? OFFSET ?;""" % (sort_by_sql)
    self.cursor.execute(sql_cmd, args)
    return self.cursor.fetchall()
    
def createObjectFromVanillaDict(class_type, vanilla_dict):
  """Simple json creates a {} dictionary object containing fields 
  we want to fill in on a new object of class class_type,
  assumes a default constructor is available"""
  o = class_type()
  for k in [x for x in o.__dict__.keys() if x[0] != "_"]:
    setattr(o, k, vanilla_dict[k])
  return o

def imgdata_to_qimage(imgdata, _format):
  "Construct a qimage from a string byte image of data as stored in the database"
  img = QtGui.QImage()
  byte_array = QtCore.QByteArray(str(imgdata))
  img.loadFromData(byte_array, _format)
  return img

def imgdata_to_qpixmap(imgdata, _format):
  "Construct q QPixmap from a string byte image of data as stored in the database"
  pixmap = QtGui.QPixmap()
  byte_array = QtCore.QByteArray(str(imgdata))
  pixmap.loadFromData(byte_array, _format)
  return pixmap

def qpixmap_to_imgdata(pixmap, _format):
  "Convert a QPixMap object to the binary string representation in the format given"
  byte_array = QtCore.QByteArray()
  byte_buffer = QtCore.QBuffer(byte_array)
  byte_buffer.open(QtCore.QIODevice.WriteOnly)
  pixmap.save(byte_buffer, _format)
  return byte_array.data()
        
class testModel(unittest.TestCase):
  
  def testSetup(self):
    dm = DBManager(0.1)
    self.assertEquals(0,dm.getNumberOfImages())
    dm.newFile()
    self.assertEquals(0,dm.getNumberOfImages())
    self.assertEquals(dm.current_db_version, dm._getCurrentDBVersion())
    dm.getMinMaxDate()
    dm.getScannedImageSet()
    dm.setTopFolderAndScanDate("/root", datetime.now())

  def testDateConversion(self):
    d = datetime.now()
    self.assertEqual(d, secondsToDate( dateToSeconds(d) ))
    
if __name__=="__main__":
  unittest.main()

    
