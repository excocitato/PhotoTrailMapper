var max_map_img_dimension = 75.0; //size of images displayed on map
var popup_img_width = 150; //size of images displayed in popup dialogs on maps..
var popup_options = {"autoPan" : false};
//map
var map = null
//list of all map markers present
var map_marker_list = [];
//cache images in here to ensure not garbage collected during asynchronous calls
var loading_images = {};
//width of arrows on lines in pixels
var arrowWidthPx = 10;
//width of arrows on lines in pixels
var arrowLengthPx = 20;
//list of all current arrow polylines
var arrowLineList = [];

var layer_opacity = 0.6;
var layer_colour = "orange";

/**
 * Object describing rectangle in latitude / longitude...
 * @returns
 */
function GeoRect(){
	this.min_lat = 0;
	this.max_lat = 0;
	this.min_lng = 0;
	this.max_lng = 0;
	/**
	 * Flag to effectively indicate if this rect is valid or should be treated as "null" with no containing
	 * elements
	 */
	this.is_valid = false;
	
	this.clone = function(){
		var c =  new GeoRect();
		c.is_valid = this.is_valid;
		c.max_lat = this.max_lat;
		c.min_lat = this.min_lat;
		c.max_lng = this.max_lng;
		c.min_lng = this.min_lng;
		return c;
	}
	
	this.copy_into = function(other){
		this.is_valid = other.is_valid;
		this.max_lat = other.max_lat;
		this.min_lat = other.min_lat;
		this.max_lng = other.max_lng;
		this.min_lng = other.min_lng;
	}
	
	this.add_element = function(lat,lng){
		if(lng === null || lat === null ){
			return;
		}
		
		if(! this.is_valid ){
			this.min_lat = lat;
			this.max_lat = lat;
			this.min_lng = lng;
			this.max_lng = lng;
			this.is_valid = true;
			return;
		}
		
		if( lng < this.min_lng){
			this.min_lng = lng;
		}
		if( lng > this.max_lng){
			this.max_lng = lng;
		}
		
		if( lat < this.min_lat){
			this.min_lat = lat;
		}
		if( lat > this.max_lat){
			this.max_lat = lat;
		}
	}
}

/**Combine 2 geo rect's together to form a new merged one*/
function combineGeoRect( rect1, rect2 ){
	if(!rect1.is_valid && !rect2.is_valid){
		return new GeoRect();
	}
	
	if(rect1.is_valid && !rect2.is_valid){
		return rect1.clone();
	}
	
	if(!rect1.is_valid && rect2.is_valid){
		return rect2.clone();
	}
	
	var merge = new GeoRect();
	merge.is_valid = true;
	
	merge.min_lat = rect1.min_lat < rect2.min_lat ? rect1.min_lat : rect2.min_lat;
	merge.max_lat = rect1.max_lat > rect2.max_lat ? rect1.max_lat : rect2.max_lat;
	merge.min_lng = rect1.min_lng < rect2.min_lng ? rect1.min_lng : rect2.min_lng;
	merge.max_lng = rect1.max_lng > rect2.max_lng ? rect1.max_lng : rect2.max_lng;
	
	return merge;
}

function createImageMarker(img_src,img_width,img_height){
	//using shadow to frame the image...
	return L.icon({
		iconUrl: img_src,
	    iconSize: [img_width, img_height],
	    shadowUrl: resource_dir + 'images/picture_border.png',
	    shadowSize: [img_width + 2, img_height + 2]
	});
}

function createMultipleImageMarker(img_src,img_width,img_height){
	return L.icon({
		iconUrl: img_src,
	    iconSize: [img_width, img_height],
	    shadowUrl: resource_dir + 'images/multiple_picture_border.png',
	    shadowSize: [img_width + 15, img_height + 15]
	});
}

function createMap(){
  //make sure map container height set first
  //adjustMapToScreenSize();

  $("#mapcontainer").append("<div id='map'></div>");
  map = L.map('map').setView([51.505, -0.09], 13);

  var mapquestUrl = 'http://{s}.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png';
  var subDomains = ['otile1','otile2','otile3','otile4'];
  var mapquestAttrib = 'Data, imagery and map information provided by <a href="http://open.mapquest.co.uk" target="_blank">MapQuest</a>,<a href="http://www.openstreetmap.org/" target="_blank">OpenStreetMap</a> and contributors.';
  var tiles = new L.TileLayer(mapquestUrl, {maxZoom: 18, attribution: mapquestAttrib, subdomains: subDomains});
  
  var london = new L.LatLng(51.505, -0.09); // geographical point (Longitude
                      // and Latitude)
  map.setView(london, 13).addLayer(tiles);
  
  // notify when map view changes...
  map.on('moveend', onMapMoved);
  map.on('popupclose', onPopupClosed);
  
  //try to disable hyperlinks...
  $("a").attr("href", "javascript:void(0);");

}

function onMapMoved(e){
	var centre = map.getCenter();
	var bounds = map.getBounds();
	var size = map.getSize();
	var params = {"centre-lat":centre.lat, "centre-lng":centre.lng, "zoom":map.getZoom(), "south":bounds.getSouthWest().lat, "north":bounds.getNorthEast().lat, "west":bounds.getSouthWest().lng, "east":bounds.getNorthEast().lng,"map_width":size.x,"map_height":size.y};
	call_server("mapMoved", params);
}

/**This is called by the server when new images have been processed*/
function mapDataChanged(){
  //force an update
  onMapMoved();
}

function onPopupClosed(e){
	//remove any highlighted row on the table
	clearHighlightedImageRows();
}

/**Call to server to un-highlight image in photo table*/
function clearHighlightedImageRows(){

}

/**Call to server to highlight image in table list*/
function highlightImageRow(image_id){
	call_server("mapPhotoHighlighted", {"image_id" : image_id});
}

function startMapNonTableMarkerUpdate(){
	onMapMoved(null);
}


function clearMap(){
	$("#map").remove();
	map = null;
	map_marker_list = [];
}

function setMapPosition(centre_lat, centre_lng, zoom){
	map.setView(new L.LatLng(centre_lat,centre_lng), zoom);
}

function panMapTo(centre_lat, centre_lng){
	map.panTo(new L.LatLng(centre_lat, centre_lng));
}

function plotArrow(start_lat_lng, end_lat_lng)
{
	var polyline = L.polyline([start_lat_lng, end_lat_lng], {color: layer_colour, opacity:layer_opacity}).addTo(map);
	arrowLineList.push(polyline);
	
	//draw direction arrow on the line
	//going to work in pixels as this is much more straightforward
	var start_px_pt = map.latLngToLayerPoint(start_lat_lng);
	var end_px_pt = map.latLngToLayerPoint(end_lat_lng);
	
	var vector_x = (end_px_pt.x - start_px_pt.x);
    var vector_y = (end_px_pt.y - start_px_pt.y);
    
    if( vector_x == 0 && vector_y == 0 ){
    	return; //abort, zero length line....
    }
    
    //calculate normalised vector along the direction of the line
    var line_length = Math.sqrt(vector_x*vector_x + vector_y*vector_y);
    vector_x = vector_x / line_length;
    vector_y = vector_y / line_length;
    
    
    //calculate the right angle vector to the line
    var rghtanglLine_x = vector_y;
    var rghtanglLine_y = - vector_x;
    
    var midPointX = ( start_px_pt.x + end_px_pt.x ) / 2;
    var midPointY = ( start_px_pt.y + end_px_pt.y ) / 2;

    
    //how long do we want the direction arrow to be in lat/lng co-oords? 
    var backArrowPtX = midPointX - ( arrowLengthPx * vector_x );
    var backArrowPtY = midPointY - ( arrowLengthPx * vector_y );
    
    var triangle_pts = [map.layerPointToLatLng( L.point(midPointX, midPointY) ),
                        map.layerPointToLatLng( L.point(backArrowPtX + ( arrowWidthPx * rghtanglLine_x / 2),
                        		                        backArrowPtY + ( arrowWidthPx * rghtanglLine_y / 2 ))),
                        map.layerPointToLatLng( L.point(backArrowPtX - ( arrowWidthPx * rghtanglLine_x / 2),
                        								backArrowPtY - ( arrowWidthPx * rghtanglLine_y / 2)))];
    
    var arrow_poly = L.polygon(triangle_pts, {color: layer_colour, fillColor : layer_colour, fill: true, fillOpacity:layer_opacity, opacity:layer_opacity}).addTo(map);
    arrowLineList.push(arrow_poly);
}

function setMapMarkers(marker_data_list, arrow_list){
	//plot arrows first
	clearArrowList();
	arrow_list = eval(arrow_list)
	$.each(arrow_list, function(index, arrow){
		//(start_lng, start_lat), (end_lng, end_lat)
		var start = L.latLng(arrow[0][1], arrow[0][0]);
		var end = L.latLng(arrow[1][1], arrow[1][0]);
		plotArrow(start,end);
	});
	
	
	marker_data_list = eval(marker_data_list);
	
	clearMapMarkers();
	
	$.each(marker_data_list, function(index, marker_data){
		plotMapMarker(marker_data.image_id_list, marker_data.lat, marker_data.lng, marker_data.draggable, marker_data.thumbnail);
	});
	
}

function clearArrowList(){
	$.each(arrowLineList, function(index, polyline){
		map.removeLayer(polyline);
	});
	
	arrowLineList = [];
}

function clearMapMarkers(){
	
	$.each(map_marker_list, function(index,marker){
		map.removeLayer(marker);
	});
	
	map_marker_list = [];
}

function format_filename(fn){
	var max_length = 30;
	if(fn.length < max_length){
		return fn;
	}
	else{
		return "..." + fn.substr(fn.length - max_length,fn.length);
	}
}

function secondsToDate(secs){
	return new Date(Math.round(secs * 1000));
}

function dateToSeconds(d){
	return d.getTime() / 1000;
}

var DateMap = { 1 : "Jan", 2 : "Feb", 3 : "Mar", 4 : "Apr", 5 : "May", 6 : "Jun", 7 : "Jul", 8 : "Aug",
	            9 : "Sept", 10 : "Oct", 11 : "Nov", 12 : "Dec" };

function intToDoubleDigitStr(i){
	if(i >= 10){
		return "" + i;
	}
	else{
		return "0" + i;
	}
}

function formatDate(d){
	var curr_day = d.getDate();
    var curr_month = DateMap[d.getMonth() + 1]; //Months are zero based
    var curr_year = d.getFullYear().toString().substring(2,4);
    return curr_day.toString() + " " + curr_month + " " + curr_year + " " + intToDoubleDigitStr(d.getHours()) + ":" + intToDoubleDigitStr(d.getMinutes());
}

function formatSeconds(s){
	return formatDate(secondsToDate(s));
}

function date_type_str(date_type){
	if( date_type === 0 ){
		return "Taken Date";
	}
	else if( date_type == 1){
		return "File Date";
	}
	else{
		return "";
	}
}

function format_taken_data(date_taken_type, seconds){
	var date_str = formatSeconds(seconds);
	var taken_str = date_type_str(date_taken_type);
		
	return taken_str + " " + date_str + ".";
}

function base64_img_src(base64){
	return 'data:image/jpeg;base64,' + base64;
}

function base64_img(base64, opts){
	var width;
	
	if( opts == null ){
		width = 75;
	}
	else{
		width = opts.width;
	}
	
	if(base64 !== ""){
		return "<img src='" + base64_img_src(base64) + "' width='" + width + "' alt='thumbnail'></img>";
	}else{
		return "";
	}
}


function plotMapMarker(image_id_list, lat, lng, draggable, icon_base64){
	if( lng !== null && lat !== null && image_id_list.length > 0){
		//first load the image so we can know it dimensions and most importantly
		//it's aspect ratio
		var img = new Image();
		img.onload = function(){ plotMapMarkerWithKnownImage(image_id_list, lat, lng, icon_base64, draggable, this);};
		img.src = base64_img_src(icon_base64);
		loading_images[img] = true; //make sure not garbage collected
	}
}

function plotMapMarkerWithKnownImage(image_id_list, lat, lng, icon_base64, draggable, loaded_image){
	delete loading_images[loaded_image];
	
	var latlng = new L.LatLng(lat,lng);
	var nat_height = loaded_image.naturalHeight;
	var nat_width = loaded_image.naturalWidth;
	
	var scaler;
	
	if(nat_height > nat_width){
		scaler = max_map_img_dimension / nat_height; 
	}
	else{
		scaler = max_map_img_dimension / nat_width;
	}
	
	var scaled_width = Math.round(nat_width * scaler);
	var scaled_height = Math.round(nat_height * scaler);
	
	var icon;
	if(image_id_list.length == 1){
		icon = createImageMarker(base64_img_src(icon_base64), scaled_width, scaled_height);
	}
	else{
		icon = createMultipleImageMarker(base64_img_src(icon_base64), scaled_width, scaled_height);
	}
	
	var marker = L.marker([lat,lng],{"icon":icon, "draggable":draggable});
	
	marker.image_id_list = image_id_list; //record the id list associated with the marker
	map_marker_list.push(marker);
	
	// is it a single marker here?
	if(image_id_list.length == 1){
		marker.on("click", function(e){onSingleMarkerClick(e.target, image_id_list[0]);});
	}
	else{
		marker.on("click", function(e){onMultipleMarkerClick(e.target, image_id_list);});
	}
	
	//connect to drag event
	if(draggable){
		marker.on("dragend", function(e){onMarkerDragged(e.target, image_id_list);});
	}
	
	marker.addTo(map);
}

function image_popup_html(image_data){
	return "<div>" + base64_img_src(image_data.thumbnail) + "</div>" + 
	        "<div>" + format_filename(image_data.filename) + "</div>" +
	        "<div>" + format_taken_data(image_data.taken_date_type, image_data.taken_date) + "</div>";
}

function onSingleMarkerClick(marker, image_id){
	var marker_index = map_marker_list.indexOf(marker);	
	var params = {"callback": "onSingleMarkerClickInfo", "curried": marker_index, "image_id": image_id};
	call_server("getImageData", params);
}

function onSingleMarkerClickInfo(marker_index, image_data){
	if( marker_index >= 0 && marker_index < map_marker_list.length){
		var marker = map_marker_list[marker_index];
		marker.unbindPopup();
		var popup = image_popup_html(image_data);
		marker.bindPopup(popup, popup_options).openPopup();
		clearHighlightedImageRows();
		highlightImageRow(marker.image_id_list[0]);
	}
}

function image_popup_html(image_data){
	return "<div>" + base64_img(image_data.thumbnail, {"width":popup_img_width}) + "</div>" + 
	        "<div>" + format_filename(image_data.filename) + "</div>" +
	        "<div>" + format_taken_data(image_data.taken_date_type, image_data.taken_date) + "</div>";
}

function onMultipleMarkerClick(marker, image_id_list){
	// lazy load one image at a time
	var marker_index = map_marker_list.indexOf(marker);
	var params = {"callback": "onMultipleMarkerClickInfo", 
			      "curried": {"marker_index":marker_index,"image_id_list":image_id_list}, 
				  "image_id": image_id_list[0]};
	call_server("getImageData", params);
}

function onMarkerDragged(marker, image_id_list){
	//tell server the images have been used
	var params = {"image_id_list": image_id_list,
			      "latitude": marker.getLatLng().lat,
			      "longitude": marker.getLatLng().lng};
	call_server("imagesDragged", params);
}

function createPrevImageDiv(marker_index){
	var marker = map_marker_list[marker_index];
	var isFirst = marker.current_image_index == 0;
	
	if( ! isFirst ){
		return "<div class='prevImage'><a onclick='prevImage(" + marker_index + ");'><img src='images/media-seek-backward.png' alt='Prev Image'></img></a></div>";
	}
	else{
		return "";
	}
}

function createNextImageDiv(marker_index){
	var marker = map_marker_list[marker_index];
	var isLast = marker.current_image_index == marker.image_id_list.length - 1;
	
	if( !isLast ){
		return "<div class='nextImage'><a onclick='nextImage(" + marker_index + ");'><img src='images/media-seek-forward.png' alt='Next Image'></img></a></div>";
	}
	else{
		return "";
	}
}

function prevImage(marker_index){
	var marker = map_marker_list[marker_index];
	marker.current_image_index = marker.current_image_index - 1;
	var params = {"callback": "onPopupImageImgData", 
		      "curried": {"marker_index":marker_index}, 
			  "image_id": marker.image_id_list[marker.current_image_index]};
	call_server("getImageData", params);
}

function nextImage(marker_index){
	var marker = map_marker_list[marker_index];
	marker.current_image_index = marker.current_image_index+1;
	var params = {"callback": "onPopupImageImgData", 
		      "curried": {"marker_index":marker_index}, 
			  "image_id": marker.image_id_list[marker.current_image_index]};
	call_server("getImageData", params);
}

function onPopupImageImgData(curried, image_data){
	var marker_index = curried.marker_index;
	$("#marker_" + marker_index).html(createMultiplePopupContent(marker_index,image_data));
	var marker = map_marker_list[marker_index];
	clearHighlightedImageRows();
	highlightImageRow(marker.image_id_list[marker.current_image_index]);	
}

function createMultiplePopupContent(marker_index,image_data){	
	var marker = map_marker_list[marker_index];
	
	return  "<div>" + base64_img(image_data.thumbnail, {"width":popup_img_width}) + "</div>" + 
		    "<div>" + format_filename(image_data.filename) + "</div>" +
		    "<div>" + format_taken_data(image_data.taken_date_type, image_data.taken_date) + "</div>" +
		    "<div>" + "Camera: " + image_data.camera_make + "</div>" + 
		    "<div>" + createPrevImageDiv(marker_index) + 
		    " " + (marker.current_image_index + 1) + " of " + marker.image_id_list.length + " " + 
		    createNextImageDiv(marker_index) + "</div>";
}

function multiple_popup_html(marker_index,image_data){
	return "<div id='marker_" + marker_index + "'>" + createMultiplePopupContent(marker_index,image_data) + "</div>";
}

function onMultipleMarkerClickInfo(curried, image_data){
	// do something sensible that allows us to iterage over the image list
	var marker_index = curried.marker_index;
	var image_id_list = curried.image_id_list;
	if( marker_index >= 0 && marker_index < map_marker_list.length){
		var marker = map_marker_list[marker_index];
		marker.unbindPopup();
		marker.image_id_list = image_id_list;
		marker.current_image_index = 0;
		var popup = multiple_popup_html(marker_index,image_data);
		marker.bindPopup(popup, popup_options).openPopup();
		highlightImageRow(marker.image_id_list[0]);
	}
}

function allowDrop(ev) {
    ev.preventDefault();
}

function drop(ev) {
	debug("drop");
    ev.preventDefault();
    var data = ev.dataTransfer.getData("Text");
    debug("data: " + data);
}