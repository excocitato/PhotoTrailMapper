function call_server(server_fn, fn_params_dict){
	if( typeof server_connection !== "undefined" ){
		server_connection.call_server(server_fn, $.toJSON(fn_params_dict))
	}
}

function call_gui(func, fn_params_dict){
	if( typeof server_connection !== "undefined" ){
		server_connection.call_gui( func, $.toJSON(fn_params_dict))
	}
}

function debug(msg){
	if( typeof server_connection !== "undefined" ){
		server_connection.debug_out(msg);
	}
}