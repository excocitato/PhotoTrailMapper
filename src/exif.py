from PySide import QtCore, QtGui
import exif_parser
import os
import time
from datetime import datetime
import types
import traceback
import model

thumbnail_min_dimension = 150 #in pixels
thumbnail_img_format = "JPG"

process_file_extensions = [ ".jpg" ]
process_file_extensions = [m.lower() for m in process_file_extensions]

#Some interesting tags 
class KnownTags(object):
  "Tags that are present in the exif data format"
  GPSLatLong = "GPS GPSLatLong"
  GPSLatitude = "GPS GPSLatitude"
  GPSLatitudeRef = "GPS GPSLatitudeRef"
  GPSLongitude = "GPS GPSLongitude"
  GPSLongitudeRef = "GPS GPSLongitudeRef"
  DateTime = "EXIF DateTimeOriginal"
  Model = "Image Model" #phone/camera model
  Make = "Image Make" #manufacturer
  ExifVersion = "EXIF ExifVersion"
  JPEGThumbnail = "JPEGThumbnail"
  
class ParsedTags(object):
  "Tags for our parsed data that we emit"
  GPSInfo = "GPSInfo"
  Thumbnail = "Thumbnail"
  DateTime = KnownTags.DateTime
  DateTimeType = "DateTimeType"
  Model = KnownTags.Model
  Make= KnownTags.Make
  ExifVersion = KnownTags.ExifVersion

  
def isDegreeMinSecType(x):
  return type(x) == types.ListType and \
         len(x) == 3 and \
         type(x[0]) == exif_parser.Ratio and \
         type(x[1]) == exif_parser.Ratio and \
         type(x[2]) == exif_parser.Ratio
         
def isLatRefType(x):
  return x in ["N","S"]

def isLonRefType(x):
  return x in ["W","E"]

def ratioToFloat(r):
  if r.den != 0:
    return float(r.num) / float(r.den)
  else:
    return 0
  

def convertDegMinSec(x):
  degrees = ratioToFloat(x[0])
  minutes = ratioToFloat(x[1])
  seconds = ratioToFloat(x[2])  
  total_degrees = degrees + minutes / 60.0 + seconds / 60.0 / 60.0
  return total_degrees

def parseLatLong( exif_data ):
  "Return (latitude,longitude) from exif tags"
  #see doc for explanation page 52
  if KnownTags.GPSLatitude not in exif_data or\
     KnownTags.GPSLongitude not in exif_data:
    return None
  
  #this is encoded in degrees/minutes/seconds we want to convert to decimal
  latitude_deg_min_secs = exif_data[KnownTags.GPSLatitude].values
  if KnownTags.GPSLatitudeRef in exif_data:
    latitude_ref = exif_data[KnownTags.GPSLatitudeRef].values
  else:
    latitude_ref = "N"
    
  longitude_deg_min_secs = exif_data[KnownTags.GPSLongitude].values
  
  if KnownTags.GPSLongitudeRef in exif_data:
    longitude_ref = exif_data[KnownTags.GPSLongitudeRef].values
  else:
    longitude_ref = "E"
 
  #ensure the types are what we expect
  if not isDegreeMinSecType(latitude_deg_min_secs) or \
     not isDegreeMinSecType(longitude_deg_min_secs) or \
     not isLatRefType(latitude_ref) or\
     not isLonRefType(longitude_ref):
    return None
  
  lat = convertDegMinSec(latitude_deg_min_secs)
  lng = convertDegMinSec(longitude_deg_min_secs)
  
  if latitude_ref == 'S':
      lat = -lat
  if longitude_ref == 'W':
      lng = -lng
  return (lat,lng)
  
def parseString(exif_data, tag):
  "Parse out the exif string, remove any whitespace and nonvisible characters..."
  tag = exif_data.get(tag, None)
  if tag == None or not hasattr(tag,"values") or not isinstance(tag.values, basestring) or len(tag.values) == 0:
    return ""
  s = tag.values
  s = s.strip()
  buf = ""
  for c in s:
    if ord(c) >= 32:
      buf = "%s%s" % (buf, c)
    else:
      break
  return buf.strip()
  
def parseInt(exif_data, tag):
  "Parse out an integer from exif"
  try:
    return int( parseString(exif_data,tag) )
  except:
    return None
    
known_date_formats = ["%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y\\%m\\%d %H:%M:%S"]

def parseDateTime(exif_data, tag):
  "Parse out the datetime string"
  #    The date and time when the original image data was generated. For a DSC the date and time the picture was taken 
  #are recorded. The format is "YYYY:MM:DD HH:MM:SS" with time shown in 24-hour format, and the date and time 
  #separated by one blank character [20.H]. When the date and time are unknown, all the character spaces except 
  #colons (":") may be filled with blank characters, or else the Interoperability field may be filled with blank characters. 
  #The character string length is 20 bytes including NULL for termination. When the field is left blank, it is treated as 
  #unknown.
  date_string = parseString(exif_data,tag)
  if date_string != None and len(date_string) != 0:
    for date_format in known_date_formats:
      try:
        #need to convert from struct time to datetime
        return datetime.fromtimestamp(time.mktime( time.strptime(date_string, date_format)))
      except Exception:
        pass
  return None
    
    
parserMap = { KnownTags.DateTime : lambda exif_data : parseDateTime( exif_data, KnownTags.DateTime ),
              KnownTags.Model : lambda exif_data : parseString( exif_data, KnownTags.Model ),
              KnownTags.Make : lambda exif_data : parseString(exif_data, KnownTags.Make),
              KnownTags.ExifVersion : lambda exif_data : parseString(exif_data, KnownTags.ExifVersion) }

def gen_thumbnail(file_name):
  "Returns a jpeg thumbnail of the image in a binary string if possible or None if this failed"
  i = QtGui.QImage()
  if not i.load(file_name):
    return None
  
  img_size = i.size() #returns QSize
  
  if img_size.width() >= img_size.height():
    ratio = float( thumbnail_min_dimension ) / img_size.width()
  else:
    ratio = float( thumbnail_min_dimension ) / img_size.height()
  
  img_size.setWidth(ratio * img_size.width() )
  img_size.setHeight( ratio * img_size.height() )
    
  thumbnail_qimage = i.scaled( img_size )
  
  #save thumbnail into QByteArray and thence into python string
  byte_array = QtCore.QByteArray()
  _buffer = QtCore.QBuffer(byte_array)
  _buffer.open(QtCore.QIODevice.WriteOnly)
  thumbnail_qimage.save(_buffer, thumbnail_img_format)
  
  py_binary_str = _buffer.data()
  _buffer.close()
  
  return py_binary_str

def get_exif(fn):
  "Get exif data from image,along with a thumbnail, fn=filename"
  #exif parsing that comes with PIL does not seem to be correct, this is perhaps better but still worrying
  #number of special cases
  ret = {}
  #get a thumbnail
  try:
    ret = exif_parser.process_file(fn, details=False)
    #use any embedded thumbnail to save time
    if KnownTags.JPEGThumbnail in ret:
      ret[ParsedTags.Thumbnail] = ret[KnownTags.JPEGThumbnail]
    else:
      ret[ParsedTags.Thumbnail] = gen_thumbnail(fn)
  except:
    #TODO want some way to record the failure!!!
    traceback.print_exc()

  return ret
  
def parseExif(fn):
  "Parse known exif tags"
  exif_raw_map = get_exif(fn)
  parsed = {}
  
  try:
    lat_long = parseLatLong(exif_raw_map)
    if lat_long != None:
      parsed[ ParsedTags.GPSInfo ] = lat_long
  except:
    traceback.print_exc()
    
  try:
    if ParsedTags.Thumbnail in exif_raw_map:
      parsed[ParsedTags.Thumbnail] = exif_raw_map[ParsedTags.Thumbnail]
  except:
    traceback.print_exc()
    
  for k in parserMap:
    try:
      v = parserMap[k](exif_raw_map)
      if v != None:
        parsed[k] = v
    except Exception:
      parsed[k] = None
      traceback.print_exc()
      
  #check if we found a date time in which case it's the time the photo 
  #was created, otherwise we will use the file date and mark up which one is which
  if ParsedTags.DateTime in parsed and parsed[ParsedTags.DateTime] != None \
     and parsed[ParsedTags.DateTime] != "":
    parsed[ParsedTags.DateTimeType] = model.ImageTable.TAKEN_DATE_FROM_EXIF
  else:
    parsed[ParsedTags.DateTime] = datetime.fromtimestamp(os.path.getctime(fn))
    parsed[ParsedTags.DateTimeType] = model.ImageTable.DATE_FROM_FILE
  return parsed
  
def findOneOf( matchList, target ):
  target_ext = os.path.splitext(target)[1].lower()
  return target_ext in matchList
    
def recurseExtract(top_dir, exif_consumerFn, abortFn, sleep_time = None):
  """top_dir is the directory to start walking down
  exif_consumerFn is a function which takes ( filepath, parsedExifMap )
  abortFn takes no params, returns True if want to abort"""
  for root, _, filenames in os.walk( top_dir ):
    print "Processing", root  
    exif_files = [x for x in filenames if findOneOf(process_file_extensions, x)]
    for e in exif_files:
      fqn = os.path.join( root, e )
      if sleep_time != None:
        time.sleep(sleep_time)
      try:
        exif_consumerFn( fqn,  parseExif(fqn) )
      except:
        traceback.print_exc()
    
    #check for abort
    if abortFn():
      break
    
class RecurseExifTask(QtCore.QThread):
  "Worker thread that does recursive exif scan"
  
  #this event is fired for each image processed
  #the parameters are the fully qualified file name and a dict of
  #parsed data tags from ParsedTags
  processedImgSignal = QtCore.Signal(str,dict)
  
  #this event is fired once the scan is complete
  scanCompleteSignal = QtCore.Signal()
  
  SLICE_TIME = 0.01
  
  def __init__(self, top_dir):
    super(RecurseExifTask, self).__init__()
    self.top_dir = top_dir
    self._abort_flag = False #set to True to cancel this thread
    
  def __str__(self):
    return "Scanning %s." % self.top_dir
     
  def _getAborting(self):
    return self._abort_flag
    
  def run(self):
    #make a consumer function that fires our QT signal
    def consumeData(fqn,exif_map):
      self.processedImgSignal.emit(fqn,exif_map)
    
    recurseExtract(self.top_dir, consumeData, self._getAborting, sleep_time=self.SLICE_TIME)
    #fire complete event
    self.scanCompleteSignal.emit()
    
  def exit(self,return_code):
    self._abort_flag = True
    
  def quit(self):
    self._abort_flag = True
    

if __name__ == "__main__":
  parseExif(r"C:\Users\tom\Pictures\geotagged\algiers.jpg")