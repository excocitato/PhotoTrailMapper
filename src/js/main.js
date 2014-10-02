var resource_dir = document.location.href.split( '/' ).slice(0,-1).join("/") + "/";

function adjustMapToScreenSize(){
	var wnd_height = $(window).height();
	var map = $("#mapcontainer");
	
	if(map.length != 0){
		var map_top = map.offset().top;
		var new_map_height = wnd_height - 20;
		
		if( new_map_height != map.height() ){
			map.height(new_map_height);
		}
	}
}

function onWndResize(){
	adjustMapToScreenSize();
}


$(document).ready(function() {
 //$(window).resize(onWndResize);
 createMap();
});