from django import template
import json
import ntpath

register = template.Library()


@register.filter(name='n3')
def n3(filename):
    """
    :param filename:
    :return: file name with suffix .n3
    """

    return filename.rsplit(".", 1)[0] + ".n3"


def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


@register.filter(name='kill_path')
def kill_path(path):
    """
    :param path:
    :return: file without path
    """
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


@register.filter(name='model_as_table')
def model_as_table(model, num_rows=-1):
    result = '<table class="table_view">'
    result += model_header_as_table(model)
    result += model_content_as_table(model, num_rows)
    result += '</table>'
    return result


@register.filter(name='model_as_table_predicate')
def model_as_table_predicate(model, num_rows=-1):
    result = '<table class="table_view">'
    result += model_header_as_table_predicate(model)
    result += model_content_as_table(model, num_rows)
    result += '</table>'
    return result


@register.filter(name='model_as_table_object')
def model_as_table_object(model, pagination):
    result = '<table class="table_view">'
    result += model_header_as_table_object(model)
    result += model_content_as_table(model, pagination)
    result += '</table>'
    return result


@register.filter(name='model_as_thead')
def model_header_as_table(model):
    model = json.loads(model)
    headers = []
    for col in model['columns']:
        if 'col_num_new' not in col or col['col_num_new'] > -1:  # show column
            headers.append(col['header']['orig_val'])

    result = "<thead>"
    result += "<tr>"

    for i, field in enumerate(headers):
        result += '<td id="id_table_head_' + str(i + 1) + '">'
        result += field
        result += "</td>"

    result += "</tr>"
    result += "</thead>"

    return result


@register.filter(name='model_as_tbody')
def model_content_as_table(model, pagination):
    '''
    pagination can be 
    int number: first x elements will be selected
    dict of 'pagination', with page and perPage attributes as in views.py -> csv_object function
    '''
    model = json.loads(model)
    #num_rows = model['num_cols_selected']
    content = []
    #p = False
    f = 0

    if isinstance(pagination, dict) and 'page' in pagination and 'perPage' in pagination:
        #p = True
        f = (pagination['page'] - 1) * pagination['perPage']
        #t = f + pagination['perPage']

    for col in model['columns']:
        if 'col_num_new' not in col or col['col_num_new'] > -1:  # show column
            row = []

            #if p:
            #    fields = col['fields'][f:t]
            if isinstance(pagination, int):
                fields = col['fields'][:pagination]
            else:
                fields = col['fields']

            for elem in fields:
                row.append(elem['orig_val'])
            content.append(row)

    content = list(zip(*content))

    result = "<tbody>"

    for i, row in enumerate(content):
        result += "<tr>"
        for j, field in enumerate(row):
            result += '<td id="id_table_field_' + str(j + 1) + '_' + str(i + 1 + f) + '">'
            result += '<span>' + field + '</span>'
            result += "</td>"
        result += "</tr>"

    result += "</tbody>"

    return result


@register.filter(name='model_as_thead_predicate')
def model_header_as_table_predicate(model):
    model = json.loads(model)
    # num_rows = model['num_cols_selected']
    headers = []
    for col in model['columns']:
        if not 'col_num_new' in col or col['col_num_new'] > -1:  # show column
            headers.append(col['header']['orig_val'])

    result = "<thead>"

    result += "<tr>"
    for i, field in enumerate(headers):
        result += '<td id="id_table_head_' + str(i + 1) + '">'
        result += field
        result += "</td>"
    result += "</tr>"

    result += "<tr>"
    for i, field in enumerate(headers):
        result += '<td>'
        result += '<input type="text" value="' + field + '" id="search_textinput_' + str(
            i + 1) + '" onkeyup="delayedOracleCall(' + str(i + 1) + ')" autocomplete="off">'
        result += '<i id="icon_' + str(i + 1) + '" class="fa fa-search" onclick="askOracle(' + str(i + 1) + ')"></i>'
        result += '<br><div id="result_area_' + str(i + 1) + '">'
        result += '<div class="bb_select" id="search_result_' + str(i + 1) + '">'
        result += '</div></div>'
        result += '</td>'
    result += "</tr>"

    result += "</thead>"

    return result


@register.filter(name='model_as_thead_object')
def model_header_as_table_object(model):
    model = json.loads(model)
    # num_rows = model['num_cols_selected']
    headers = []
    for col in model['columns']:
        if col['col_num_new'] > -1:  # show column
            headers.append(col['header']['orig_val'])

    result = "<thead>"

    result += "<tr>"
    for i, field in enumerate(headers):
        result += '<td id="id_table_settings_' + str(i + 1) + '">'
        result += '<select>'
        result += '<option>no action</option>'
        result += '<option>add URIs</option>'
        result += '<option>add data type</option>'
        result += '</select>'
        result += '</td>'
    result += "</tr>"

    result += "<tr>"
    for i, field in enumerate(headers):
        result += '<td id="id_table_head_' + str(i + 1) + '">'
        result += field
        result += "</td>"
    result += "</tr>"

    result += "</thead>"

    return result
