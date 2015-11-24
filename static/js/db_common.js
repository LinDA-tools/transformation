
function get_db_model(){
    var model = $("#id_hidden_model");
    if(model.length > 0) {
        if(model.val().length > 0) {
            return JSON.parse(model.val().replace(/'/g,"\""));
        }
    }
    else return false;
}



// creates rdf triple view
function dbmodel_to_table(model){

    console.log("dbmodel_to_table()");
    
    var rdf_prefix = model['prefixes']; // var rdf_prefix = $("#id_hidden_rdf_prefix_field");    
//    console.log("  rdf_prefix.val():" + rdf_prefix.val());
//    if (rdf_prefix.val().length > 0)
//        rdf_prefix = JSON.parse(rdf_prefix.val().replace(/'/g,"\""));
//    console.log("  rdf_prefix.val():" + rdf_prefix.val());
    
    
    var tbl = jQuery('<table/>', {
        class: "rdf_table"
    });//.appendTo(elem);

    if(model == undefined){
        return tbl;
    }

    for (var t = 0; t < model['tables'].length; t++) {
//        console.log("t: " + t);
        var table = model['tables'][t];
        var base_iri = model['tables'][t].base_iri;
        var num_cols = table['columns'].length;
        var num_selected_cols = 0;
        var selected_cols_list = [];
        for(var i = 0; i < num_cols; i++) {
            if (table['columns'][i]['selected'] == "true") {
                num_selected_cols++;
                selected_cols_list.push(table['columns'][i].name);
            }
        }

//        var num_selected_cols = table['columns'].length;
//        console.log("  num_selected_cols: " + num_selected_cols);


        var subject_uri = table['subject_uri'];
        console.log("  subject_uri: " + subject_uri);

        var this_pk_list = [];
        var this_pk_list_c = [];
        if (typeof subject_uri != "undefined") {
            while (subject_uri.length > 0) {
                var pk_index = subject_uri.search(/{.*?}/);
                if (pk_index > -1) {
                    var pk = subject_uri.match(/{.*?}/)[0];
                    this_pk_list_c.push(pk);
                    pk = pk.substring(1, pk.length-1);
                    this_pk_list.push(pk);
                    var substr_start = pk_index + pk.length + 2;
                    var substr_length = subject_uri.length - substr_start;
                    subject_uri = subject_uri.substr(substr_start , substr_length);
                }
            }
        }
//        subject_uri = table['subject_uri'];
        
//        var this_pk_list = subject_uri.split(delimiter_symbol);

        var numrows = num_selected_cols * table['values_10_selected'].length;
//        console.log("  num_selected_cols: " + num_selected_cols);
//        console.log("table['subject_uri']: " + table['subject_uri']);
//        console.log("table['columns']: " + table['columns'][0]);
//        console.log("table['columns']: " + table['columns'][1]);
        //create table content
        var obj_array = [];
        
        for(var i = 1; i < table['values_10_selected'].length; i++){
//            console.log("i: " + i);
//            var tr = jQuery('<tr/>', {} );
            for(var j = 0; j < num_selected_cols; j++){
//                console.log("j: " + j);
                obj_array.push(table['values_10_selected'][i][j]);
            }
        }
        
//        console.log("  obj_array.length " + obj_array.length);

        var enrich_array = table['enrich'];
        var firstrun = true;
        for(var i = 0, j = 0, k = 1; i < obj_array.length; i++, j++) {
            subject_uri = table['subject_uri'];
            var isNull = false;
            if (j == num_selected_cols) {
                j = 0;
                k++;
                firstrun = true;
            }
            if (typeof enrich_array != "undefined" && firstrun) {                
                for (var l=0; l < enrich_array.length; l++) {
                    var prefix = enrich_array[l].prefix;
                    var tr = jQuery('<tr/>', {} ).attr({
                        id: "id_rdf_subject_" + table.name + "_" + k.toString() + "_" + l.toString()
                    });
                    var td1 = jQuery('<td/>', {} );
                    var subject_str = base_iri;
                    
                    for (var ii = 0; ii < this_pk_list.length; ii++) {
                        for (var jj = 0; jj < num_selected_cols; jj++) {
                            if (this_pk_list[ii] == table['columns'][jj].name) {
                                subject_uri = subject_uri.replace(this_pk_list_c[ii], table['values_10'][k][jj]);
                            }
                        }
                    }
                    if (typeof base_iri != "undefined" && base_iri.length > 0) {
                        subject_str = "<" + subject_str + subject_uri + ">";
                    } else {
                        subject_str = "_:" + subject_uri;
                    }
                    
                    td1.text(subject_str).attr({
                        id: "id_rdf_subject_" + table.name + "_" + k.toString() + "_" + l.toString()
                    });
                    td1.appendTo(tr);

                    var td2 = jQuery('<td/>', {} ).attr({
                        id: "id_rdf_predicate_" + table.name + "_" + selected_cols_list[j] + "_" + k.toString() + "_" + l.toString()
                    });
                    td2.text("rdf:type");
                    td2.appendTo(tr);
                    
                    var td3 = jQuery('<td/>', {} ).attr({
                        id: "id_rdf_object___" + table.name + "___" + selected_cols_list[j] + "_" + k.toString() + "_" + l.toString()
                    });
                    if (prefix.prefix != "") {
                        td3.text(prefix.prefix + ":" + prefix.suffix);
                    } else {
                        td3.text(prefix.url);
                    }
                    td3.appendTo(tr);

                    var td4 = jQuery('<td/>', {});
                    td4.text(".");
                    td4.appendTo(tr);
                    tr.appendTo(tbl);
                }
            }
            firstrun = false;

            

            var tr = jQuery('<tr/>', {} ).attr({
                id: "id_rdf_subject_" + table.name + "_" + k.toString()
            });
            var td1 = jQuery('<td/>', {} );

            var subject_str = base_iri;
            
            for (var ii = 0; ii < this_pk_list.length; ii++) {
//                this_pk_list[ii] = this_pk_list[ii].replace(/{/g, '');
//                this_pk_list[ii] = this_pk_list[ii].replace(/}/g, '');
//                this_pk_list[ii] = this_pk_list[ii].replace(/\s/g, '');

//                console.log("  this_pk_list[ii]: " + this_pk_list[ii]);
                for (var jj = 0; jj < num_selected_cols; jj++) {
                    if (this_pk_list[ii] == table['columns'][jj].name) {
                        subject_uri = subject_uri.replace(this_pk_list_c[ii], table['values_10'][k][jj]);
//                        subject_str = subject_str + table['values'][k][jj] + delimiter_symbol;
//                        console.log("  subject_uri: " + subject_uri);
                    }
                }
            }
//            console.log("subject_str: " + subject_str);
            if (typeof base_iri != "undefined" && base_iri.length > 0) {
                subject_str = "<" + subject_str + subject_uri + ">";
            } else {
                subject_str = "_:" + subject_uri;
            }

//            subject_str = "<" + subject_str.substring(0, subject_str.length - 1) + ">";
//            console.log("subject_uri: " + subject_uri);
            td1.text(subject_str).attr({
                id: "id_rdf_subject_" + table.name + "_" + k.toString()
            });
            td1.appendTo(tr);
            
            var td2 = jQuery('<td/>', {} ).attr({
                id: "id_rdf_predicate_" + table.name + "_" + table.columns[j].name + "_" + k.toString()
            });

            var selected_column = $.grep(table['columns'], function (element, index) {
                return element.name == selected_cols_list[j];
            });
            
            td2.text(selected_column[0].rdf_predicate);

//            td2.text(table.columns[j].rdf_predicate);
            td2.appendTo(tr);
            var td3 = jQuery('<td/>', {} ).attr({
                id: "id_rdf_object___" + table.name + "___" + selected_column[0].name + "_" + k.toString()
            });
            if (obj_array[i] == 'None' || obj_array[i] == "" ) {
//                tr.css("visibility", "hidden");
                isNull = true;
            }
            if (typeof selected_column[0].data_type != 'undefined' && selected_column[0].data_type != "" ) {
                var new_pre = true;
                for (var ii = 0; ii < rdf_prefix.length; ii++) {
                    pre = rdf_prefix[ii];
                    if (pre['prefix'] == selected_column[0].data_type['prefix']) {
                        new_pre = false;
                    }
                }
                if (new_pre) {
                    new_pre = {'prefix': selected_column[0].data_type['prefix'], 'url': selected_column[0].data_type['url']};
                    rdf_prefix.push(new_pre);
                    $("#id_hidden_rdf_prefix_field").val(JSON.stringify(rdf_prefix));
                    
                }
                td3.text("\"" + obj_array[i] + "^^" + selected_column[0].data_type['prefix'] + ":" + selected_column[0].data_type['suffix'] + "\"" );
            } else {
                td3.text("\"" + obj_array[i] + "\"");
            }
            td3.appendTo(tr);
            var td4 = jQuery('<td/>', {});
            td4.text(".");
            td4.appendTo(tr);
            if (! isNull)
                tr.appendTo(tbl);
        }
        
    }
    if (typeof rdf_prefix != "undefined") {
        for (var i = 0; i < rdf_prefix.length; i++) {
            pre = rdf_prefix[i];
    //        console.log("  prefix: " + pre['prefix']);
    //        console.log("  url: " + pre['url']);
            var tr = jQuery('<tr/>', {} ).attr({id: pre['prefix'] });
            var td1 = jQuery('<td/>', {} );
            td1.text("@prefix");
            td1.appendTo(tr);
            var td2 = jQuery('<td/>', {} );
            td2.text(pre['prefix']);
            td2.appendTo(tr);
            var td3 = jQuery('<td/>', {} );
            td3.text("<" + pre['url'] + ">");
            td3.appendTo(tr);
            var td4 = jQuery('<td/>', {} );
            td4.text(".");
            td4.appendTo(tr);
            tr.prependTo(tbl);
        }
    }
    return tbl;
}


function model_to_table2(model) {
    var num_tables = model['tables'].length;

    for(var t = 0; t < num_tables; t++) {
        var table = model['tables'][t];
        // replace foreign keys
        var num_columns = table['columns'].length;
        for(var j = 0; j < num_columns; j++) {
        
            var column = table['columns'][j];
            if (typeof column.foreign_key_string != "undefined" && column.foreign_key_string.length > 0 ) {
                var t_table  = column.foreign_key_string.split(":")[0];
                var t_column = column.foreign_key_string.split(":")[1];
                var source_td = $("td[id^='id_rdf_object___" + table.name + "___" + column.name + "___']");
                for (var k = 0; k < source_td.length; k++) {
                    var old_val = $(source_td[k]).text();
                    if (typeof $(source_td[k]).attr("value") != "undefined") {
                        old_val = $(source_td[k]).attr("value");
                    }
                    var target_td = $("td[id^='id_rdf_subject___" + t_table + "_']");
                    for (var l = 0; l < target_td.length; l++) {
                        var td_text =  new String($(target_td[l]).text());
                        if ( td_text.search(old_val) > -1 ) {
                            var t_val =  $(target_td[l]).text();
                        }
                    }
                    var targetTable = $.grep(model['tables'], function (element, index) {
                        return element.name == t_table;
                    });
                    targetTable = targetTable[0];
                    
                    var targetColumn = $.grep(targetTable['columns'], function (element, index) {
                        return element.name == t_column;
                    });
        
                    if (targetColumn[0].isPrimaryKey ==  "PRI" ) {
                        if ( targetTable['base_iri'].length > 0 ) {
                            new_val = "<" + targetTable['base_iri'] + targetTable['subject_uri'] + ">";
                            new_val = new_val.replace("{" + t_column + "}", old_val);
                            new_val = new_val.replace(/\"/g, '');
                            $(source_td[k]).text(new_val);
                            $(source_td[k]).attr("value", old_val);                                        
                        } else {
                            new_val = "_:" + targetTable['subject_uri'];
                            new_val = new_val.replace("{" + t_column + "}", old_val);
                            new_val = new_val.replace(/\"/g, '');
                            $(source_td[k]).text(new_val);
                            $(source_td[k]).attr("value", old_val);                                        
                        }
                    }
                }
            }
        }
        if (table.handle_relTable == "true") {
            update_relTable(table);
        }
    }
}


function update_relTable( table ) {
    model = get_model();
    var fkeys = get_fkeys();

    var rel_table_values_10 = table['values_10'];
    var values_col_names = rel_table_values_10[0];
    var val_1_col_name = values_col_names[0];
    var val_2_col_name = values_col_names[1];
    
    var val_1_column = $.grep(table['columns'], function (element, index) {
        return element.name == val_1_col_name;
    });
    val_1_column = val_1_column[0];
    
    var val_2_column = $.grep(table['columns'], function (element, index) {
        return element.name == val_2_col_name;
    });
    val_2_column = val_2_column[0];
    
    var val_1_column_foreign_key_string_list = val_1_column.foreign_key_string.split(":");
    var val_1_target_table_name = val_1_column_foreign_key_string_list[0];
    var val_1_target_column_name = val_1_column_foreign_key_string_list[1];
    
    var val_2_column_foreign_key_string_list = val_2_column.foreign_key_string.split(":");
    var val_2_target_table_name = val_2_column_foreign_key_string_list[0];
    var val_2_target_column_name = val_2_column_foreign_key_string_list[1];
    
    for(var i = 1; i < rel_table_values_10.length; i++) {
        var values = rel_table_values_10[i];
        
        var val_1 = values[0];
        var val_2 = values[1];
        
        var firstelem = true;
        $("td[id^='id_rdf_object___" + table.name + "___" + val_1_col_name + "']").each(function() {
            if ('"' + val_1 + '"' == $(this).attr("value") && $(this).attr("lang") != "fr" ) {
                if (firstelem) {
                    var target_subject_td = $(this).siblings("[id^='id_rdf_subject___']");
                    var new_val = "";
                    $("td[id^='id_rdf_object___" + val_2_target_table_name + "___" + val_2_target_column_name + "']").each(function() {
                        if ('"' + val_2 + '"' == $(this).text()) {
                            var target_subject_td2 = $(this).siblings("[id^='id_rdf_subject___']");
                            new_val = $(target_subject_td2).text();
                        }
                    });
                    if (new_val != "") {
                        $(target_subject_td).text(new_val);
                        $(this).attr("lang", "fr");
                        firstelem = false;
                    } else {

                        var val_2_target_table = $.grep(model['tables'], function (element, index) {
                            return element.name == val_2_target_table_name;
                        });
                        val_2_target_table = val_2_target_table[0];
                        
                        var val_2_target_table_values_10 = val_2_target_table['values_10'];
                        var val_2_target_table_col_names = val_2_target_table_values_10[0];
                        
                        var row = 0;
                        for(var j = 1; j < val_2_target_table_values_10.length; j++) {
                            var val_2_target_table_values = val_2_target_table_values_10[j];
                            for (var k = 0; k<val_2_target_table_values.length; k++) {
                                if ( val_2 == val_2_target_table_values[k]) {
                                    row = j;
                                }
                            }
                        }
                        
                        for (var j = 0; j<val_2_target_table_col_names.length; j++) {
                            $("td[id^='id_rdf_object___" + val_2_target_table_name + "___" + val_2_target_table_col_names[j] + "']").each(function() {
                                if ('"' + val_2_target_table_values_10[row][j] + '"' == $(this).text()) {
                                    var target_subject_td2 = $(this).siblings("[id^='id_rdf_subject___']");
                                    new_val = $(target_subject_td2).text();
                                }
                            });
                            if (new_val != "") {
                                $(target_subject_td).text(new_val);
                                $(this).attr("lang", "fr");
                                firstelem = false;
                                break;
                            }
                        }
                    }
                }
            }
        });
        
        var firstelem = true;
        $("td[id^='id_rdf_object___" + table.name + "___" + val_2_col_name + "']").each(function() {
            if ('"' + val_2 + '"' == $(this).attr("value")  && $(this).attr("lang") != "fr" ) {
                if (firstelem) {
                    var target_subject_td = $(this).siblings("[id^='id_rdf_subject___']");
                    var new_val = "";
                    $("td[id^='id_rdf_object___" + val_1_target_table_name + "___" + val_1_target_column_name + "']").each(function() {
                        if ('"' + val_1 + '"'  == $(this).text()) {
                            var target_subject_td1 = $(this).siblings("[id^='id_rdf_subject___']");
                            new_val = $(target_subject_td1).text();
                        }
                    });
                    if (new_val != "") {
                        $(target_subject_td).text(new_val);
                        $(this).attr("lang", "fr");
                        firstelem = false;
                    } else {
                        var val_1_target_table = $.grep(model['tables'], function (element, index) {
                            return element.name == val_1_target_table_name;
                        });
                        val_1_target_table = val_1_target_table[0];
                        var columns = val_1_target_table['columns'];

                        var val_1_target_table_values_10 = val_1_target_table['values_10'];
                        var val_1_target_table_col_names = val_1_target_table_values_10[0];
                        
                        var row = 0;
                        for(var j = 1; j < val_1_target_table_values_10.length; j++) {
                            var val_1_target_table_values = val_1_target_table_values_10[j];
                            for (var k = 0; k<val_1_target_table_values.length; k++) {
                                if ( val_1 == val_1_target_table_values[k]) {
                                    row = j;
                                }
                            }
                        }
                        for (var j = 0; j<val_1_target_table_col_names.length; j++) {
                            new_val = "";
                            $("td[id^='id_rdf_object___" + val_1_target_table_name + "___" + val_1_target_table_col_names[j] + "']").each(function() {
                                if ('"' + val_1_target_table_values_10[row][j] + '"' == $(this).text()) {
                                    var target_subject_td1 = $(this).siblings("[id^='id_rdf_subject___']");
                                    new_val = $(target_subject_td1).text();
                                }
                            });
                            if (new_val != "") {
                                $(target_subject_td).text(new_val);
                                $(this).attr("lang", "fr");
                                firstelem = false;
                                break;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // reset lang attr
    $("td[id^='id_rdf_object___" + table.name + "___" + val_1_col_name + "']").each(function() {
        $(this).attr("lang", "");
    });

    $("td[id^='id_rdf_object___" + table.name + "___" + val_2_col_name + "']").each(function() {
        $(this).attr("lang", "");
    });
}


// AJAX for rdb_save_mapping
function rdb_save_mapping(current_page) {
    console.log("rdb_save_mapping("+current_page+")");
    //var model = get_model();
    var model = $("#id_hidden_model");
    if(model.length > 0)
        model = model.val().replace(/'/g,"\"");

    var name_mapping = prompt("Please enter a name for your transformation:", model['database']);
    if (name_mapping != null) {
        $.ajax({
            url : "rdb/save_mapping",   // the endpoint
            type : "POST",              // http method
            data : { current_page: current_page, model: model, name_mapping: name_mapping }, // data sent with the delete request
            success : function(json) {
                console.log("rdb_save_mapping successful");
            },

            error : function(xhr, errmsg, err) {
                // Show an error
                $('#results').html("<div class='alert-box alert radius' data-alert>"+
                "Oops! We have encountered an error. <a href='#' class='close'>&times;</a></div>"); // add error to the dom
                console.log(xhr.status + ": " + xhr.responseText); // provide a bit more info about the error to the console
                console.log("errmsg: " + errmsg); // provide a bit more info about the error to the console
                console.log("err: " + err); // provide a bit more info about the error to the console
            }
        });
    } else {
        return false;
    }
};



// This function gets cookie with a given name
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

var csrftoken = getCookie('csrftoken');

/*
The functions below will create a header with csrftoken
*/
function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}


function sameOrigin(url) {
    // test that a given url is a same-origin URL
    // url could be relative or scheme relative or absolute
    var host = document.location.host; // host + port
    var protocol = document.location.protocol;
    var sr_origin = '//' + host;
    var origin = protocol + sr_origin;
    // Allow absolute or scheme relative URLs to same origin
    return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
        (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
        // or any other URL that isn't scheme relative or absolute i.e relative.
        !(/^(\/\/|http:|https:).*/.test(url));
}


$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && sameOrigin(settings.url)) {
            // Send the token to same-origin, relative URLs only.
            // Send the token only if the method warrants CSRF protection
            // Using the CSRFToken value acquired earlier
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});
