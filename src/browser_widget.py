from PySide import QtCore, QtGui, QtWebKit

def toJavascriptString(s):
  "Take a python string and process it so it is handled equivalently in javascript"
  return s.replace( "\\", "\\\\" )
  
class ServerConnection(QtCore.QObject):
  "This is passed to the javascript interpretter and used to connect from javascript to server"
  
  def __init__(self, server_call):
    super(ServerConnection, self).__init__(None)
    self.server_call = server_call
    
  @QtCore.Slot(str, str)
  def call_server(self, func_name, func_params):
    "Call a method on the server"
    self.server_call( func_name, func_params )
    
  @QtCore.Slot(str)
  def debug_out(self, msg):
    "Debug info"
    print msg

class ClientMsg(object):
  "Package up calls to server from gui in one of these for queuing/processing"
  
  def __init__(self, func_name, parameter_dict):
    self.func_name = func_name
    self.parameter_dict = parameter_dict
    
  def __str__(self):
    return "%s(%s)" % (self.func_name,self.parameter_dict)

class WebPage(QtWebKit.QWebPage):
  "WebPage that actually tells us about errors!"
  def javaScriptConsoleMessage(self, msg, line, source):
    print '%s line %d: %s' % (source, line, msg)
  
class WebViewEx(QtWebKit.QWebView):
  """Derive from QWebView in order to provide more functionality"""
  
  JSON_MIME_TYPE = "application/json"
  
  def __init__(self, parent=None):
    super(WebViewEx,self).__init__(parent)
    self.setAcceptDrops(True)
    self.setMaximumHeight(100000)
    
  def dragEnterEvent(self, event):
    if self.JSON_MIME_TYPE in event.mimeData().formats():
      print "Accepting"
      return True
    else:
      return super(WebViewEx, self).dragEnterEvent(event)
  
  def dropEvent(self, event):
    if self.JSON_MIME_TYPE in event.mimeData().formats():
      print "Got some JSON"
      return True
    else:
      return super(WebViewEx, self).dropEvent(event)
  
class BrowserWidget(QtGui.QWidget):     
  
  javascript_from_server_signal = QtCore.Signal(str)
  
  def __init__(self, parent, html_file, js_server_call_fn):
    """Takes a
    html_file uri to load
    quit_function a function that returns True if the application is to quit... 
    js_server_call_fn which takes func_name, func_params both string, the params json encoded"""
    super(BrowserWidget, self).__init__()

    self.parent = parent
    self.view = WebViewEx(self)
    self.view.setPage(WebPage()) #ensure we can see javascript errros
    self.connection = ServerConnection(js_server_call_fn)
    self.setMaximumHeight(100000)
    
    #seems we need absolute paths in the html file for QtWebView to work !?
    self.view.setUrl(QtCore.QUrl.fromLocalFile(html_file))
    
    #make the connection back to the server...
    self.frame = self.view.page().mainFrame()
    self.frame.addToJavaScriptWindowObject('server_connection', self.connection)
    
    #self._sizeHint = QtCore.QSize(600,800)
    
    #adjust the size policy
    self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
    
  def initialise(self):
    "Sort out thread safe connection"
    self.javascript_from_server_signal.connect(self.javascript_from_server_slot, QtCore.Qt.QueuedConnection)
    
  #def sizeHint(self):
  #  return self._sizeHint
  
  #def setSizeHint(self, x):
  #  self._sizeHint = x
    
  @QtCore.Slot(str)
  def javascript_from_server_slot(self, jscript):
    "Handle a javascript send from the server on the QT gui thread"
    self.frame.evaluateJavaScript(jscript)
    
  def execute_script(self, jscript):
    "Evaluate javascript from the gui thread"
    self.frame.evaluateJavaScript(jscript)
    

