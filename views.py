import csv
from io import TextIOWrapper
from io import StringIO
import os
import json
from django.http import HttpResponse
from django.shortcuts import render, render_to_response
from django.template import RequestContext
import pandas as pd
from django.http import JsonResponse
import requests
from django.core.files.base import ContentFile
from .forms import *
from django.conf import settings
from .settings import API_HOST
import ast
from transformation.models import Mapping
import copy
import datetime
from itertools import chain # for concatenating ranges
import re # regex


# ###############################################
# MODELS
# ###############################################

def user_test(request):
    return render_to_response('transformation/user_test.html',
                             context_instance=RequestContext(request))

def data_choice(request):
    print("VIEW data_choice")
    #print(request.session) 
    if 'csv_rows' in request.session:
        del request.session['csv_rows']
    if 'csv_raw' in request.session:
        del request.session['csv_raw']
    if 'csv_dialect' in request.session:
        del request.session['csv_dialect']
    if 'file_name' in request.session:
        del request.session['file_name']
    if 'model' in request.session:
        del request.session['model']
    if 'rdf_array' in request.session:
        del request.session['rdf_array']
    if 'rdf_prefix' in request.session:
        del request.session['rdf_prefix']
    form = DataChoiceForm()
    mappings = Mapping.objects.filter(user=request.user.id)
    return render_to_response('transformation/data_choice.html', {'form': form, 'mappings': mappings},
                              context_instance=RequestContext(request))


def csv_upload(request):
    print("VIEW csv_upload")
    form_action = 2
    publish_message = ""
    if request.method == 'POST':
        print("PATH 1 - POST")
        # a raw representation of the CSV file is also kept as we want to be able to change the CSV dialect and then reload the page
        form = None
        csv_raw = None
        csv_rows = None
        csv_dialect = None
        uploadFileName = 'no file selected'
        # if page was loaded without selecting a file in html form    
        if not request.FILES:
            form = UploadFileForm(request.POST)
            if request.POST and form.is_valid() and form != None:
                print("PATH 1.1 - no file uploaded")
                # content  is passed on via hidden html input fields
                if form.cleaned_data['hidden_csv_raw_field']:
                    csv_raw = form.cleaned_data['hidden_csv_raw_field']
                    csv_rows, csv_dialect = process_csv(StringIO(form.cleaned_data['hidden_csv_raw_field']), form)

                else:
                    print('no raw csv')

                uploadFileName = form.cleaned_data['hidden_filename_field']

            # if page is loaded without POST
            else:
                print("PATH 1.2")

        # when an upload file was selected in html form, APPLY BUTTON
        else:  # if not request.FILES:
            print("PATH 3 - file was uploaded")

            form = UploadFileForm(request.POST, request.FILES)
            uploadFileName = request.FILES['upload_file'].name
            uploadFile = request.FILES['upload_file'].file
            #print(uploadFileName[-4:]);
            if (uploadFileName[-4:] == "xlsx" or uploadFileName[-4:] == ".xls"):
                #print(uploadFileName[-4:]);
                data_xls = pd.read_excel(request.FILES['upload_file'], 0, index_col=None)
                if not os.path.exists('tmp'):
                    os.makedirs('tmp')
                data_xls.to_csv('tmp/' + uploadFileName[:-4] + '.csv', encoding='utf-8')
                uploadFile = open('tmp/' + uploadFileName[:-4] + '.csv', "rb")
                uploadFileName = uploadFileName[:-4] + '.csv'

            if form.is_valid():
                csv_rows = []
                csvLines = []
                rows = []
                csv_dialect = {}
                csv_raw = ""

                # read/process the CSV file and find out about its dialect (csv params such as delimiter, line end...)
                # https://docs.python.org/2/library/csv.html#
                with TextIOWrapper(uploadFile, encoding=request.encoding) as csvfile:
                    #with TextIOWrapper(uploadFile, encoding='utf-8') as csvfile:
                    # the file is also provided in raw formatting, so users can appy changes (choose csv params) without reloading file 
                    csv_raw = csvfile.read()
                    csv_rows, csv_dialect = process_csv(csvfile, form)

                    #check if file is correct
                    publish_message = '<span class="green"><i class="fa fa-check-circle"></i> File seems to be okay.</span>'
                    num_last_row = len(csv_rows[0])
                    for i in range(1,len(csv_rows)):
                        if len(csv_rows[i]) != num_last_row:
                            print("File seems to be either corrupted or it was loaded with wrong parameters!")
                            publish_message = '<span class="red"><i class="fa fa-exclamation-circle"></i> File seems to be corrupt or loaded with wrong parameters!</span>'
                            break

            else:  # if form.is_valid():
                print("form not valid")

        if 'button_upload' in request.POST:
            print("UPLOAD BUTTON PRESSED")
            csv_rows = csv_rows if csv_rows else None

            request.session['csv_dialect'] = csv_dialect
            request.session['csv_rows'] = csv_rows
            request.session['csv_raw'] = csv_raw
            if 'upload_file' in request.FILES:
                request.session['file_name'] = request.FILES['upload_file'].name
            #return redirect(reverse('csv-column-choice-view'))
            html_post_data = {
                'action': form_action,
                'form': form,
                'csvContent': request.session['csv_rows'],
                'csvRaw': request.session['csv_raw'],
                'csvDialect': request.session['csv_dialect'],
                'filename': request.session['file_name'],
                'publish_message': publish_message
            }
            return render(request, 'transformation/csv_upload.html', html_post_data)

        if 'button_choose' in request.POST:
            #print(request.POST['mapping_id'])
            request.session['model'] = json.loads(Mapping.objects.filter(id=request.POST['mapping_id'])[0].mappingFile.read().decode("utf-8"))
            form = UploadFileForm()
            return render(request, 'transformation/csv_upload.html', {'action': 1, 'form': form})

    # html GET, we get here when loading the page 'for the first time'
    else:  # if request.method == 'POST':
        print("PATH 4 - initial page call (HTML GET)")
        form = UploadFileForm()
        return render(request, 'transformation/csv_upload.html', {'action': 1, 'form': form})


def csv_column_choice(request):
    print("VIEW csv_column_choice")
    form_action = 3
    reduced_model = None
    publish_message = None
    form = CsvColumnChoiceForm(request.POST)
    time1 = datetime.datetime.now()


    if not 'model' in request.session:
        print('creating model')

        arr = request.session['csv_rows']
        m = {"file_name": request.session['file_name'], "num_cols_total": len(arr), "num_cols_selected": len(arr), "columns": []}
        f = -1
        c = -1

        try:

            for i,head in enumerate(arr[0]):                
                m['columns'].append({'col_num_orig': i+1, 'fields': [], 'header': {'orig_val': arr[0][i]}})

            for field in range(1,len(arr)):
                f = field
                for col in range(0,len(arr[field])):
                    c = col
                    m['columns'][col]['fields'].append({'orig_val': arr[field][col], 'field_num': field})

        except IndexError:
            print("index error: col "+str(c)+", field "+str(f))

        request.session['model'] = m
        #print(request.session['model'])
        secs = datetime.datetime.now() - time1
        print("done "+str(secs))
        print_model_dim(request.session['model'])
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        #printfields(request.session['model'])

    elif 'model' in request.session and not 'fields' in request.session['model']['columns'][0]: #has fields? if not, only scaffolding from model 'loaded' in data choice page of wizard
        # when only a loaded model 'scaffolding'
        print("model 'scaffolding' was loaded")

        #print("mod vor laden")
        #printfields(request.session['model'])

        if len(request.session['model']['columns']) != len(inverted_csv):
            publish_message = "The file you tried to load does not fit the chosen transformation project. The number of columns is different."
        else:
            for i, col in enumerate(inverted_csv):
                request.session['model']['columns'][i]['fields'] = []
                for j, field in enumerate(col):
                    if j == 0: # table header / first row
                        #column_obj['header'] = {"orig_val": field}
                        pass
                    else:
                        request.session['model']['columns'][i]['fields'].append({"orig_val": field, "field_num": j})

        #csv_rows_selected_columns = get_selected_rows_content(request.session)
        #mark_selected_rows_in_model(request.session)

        #print("mod nach laden")
        #printfields(request.session['model'])
        print_model_dim(request.session['model'])

    elif request.POST and form.is_valid() and 'hidden_model' in form.cleaned_data and form.cleaned_data['hidden_model']:
        reduced_model = json.loads(form.cleaned_data['hidden_model'])
        request.session['model'] = update_model(request.session['model'],reduced_model)
        print_model_dim(request.session['model'])

    html_post_data = {         
        'action': form_action,
        'csvContent': request.session['csv_rows'][:10],
        #'filename': request.session['file_name'],
        'publish_message': publish_message
    }
    if 'model' in request.session and not 'rdfModel' in html_post_data:
        #printfields(request.session['model'])
        #print("------------")
        redu = reduce_model(request.session['model'], 10)
        html_post_data['rdfModel'] = json.dumps(redu)
        #printfields(redu)
        #html_post_data['rdfModel'] = request.session['model']
    #print("mod vor senden")
    #printfields(request.session['model'])
    request.session.modified = True
    #print("mod vor senden 2")
    #printfields(html_post_data['rdfModel'])
    return render(request, 'transformation/csv_column_choice.html', html_post_data)


def csv_subject(request):
    print("VIEW csv_subject")

    #print("mod direkt nach laden seite")
    #printfields(request.session['model'])

    #print(request.session['model'])
    form_action = 4
    form = SubjectForm(request.POST)
    reduced_model = None
    if request.POST and form.is_valid() and form != None:
        # content  is passed on via hidden html input fields
        '''
        if 'hidden_rdf_array_field' in form.cleaned_data:
            request.session['rdf_array'] = form.cleaned_data['hidden_rdf_array_field']

        if 'hidden_rdf_prefix_field' in form.cleaned_data:
            request.session['rdf_prefix'] = form.cleaned_data['hidden_rdf_prefix_field']
        '''

        if 'hidden_model' in form.cleaned_data:
            time1 = datetime.datetime.now()
            print("fetching model")
            #print(form.cleaned_data['hidden_model'])
            reduced_model = json.loads(form.cleaned_data['hidden_model'])
            print("red mod")
            printfields(reduced_model)

            secs = datetime.datetime.now() - time1
            print("init: "+str(secs))
            time1 = datetime.datetime.now()


            if reduced_model:
                request.session['model'] = update_model(request.session['model'], reduced_model)
                secs = datetime.datetime.now() - time1
                print("updating model: "+str(secs))
                time1 = datetime.datetime.now()


    time1 = datetime.datetime.now()
    redu = reduce_model(request.session['model'], 10)
    secs = datetime.datetime.now() - time1
    #time1 = datetime.datetime.now()
    print("reducing model: "+str(secs))
    dumped = json.dumps(redu)
    print("dunped")
    html_post_data = {
        'rdfModel': dumped,
        'action': form_action,
        #'csvContent': csv_rows_selected_columns,
        #'filename': request.session['file_name'],
        #'rdfArray': request.session['rdf_array'],
        #'rdfPrefix': request.session['rdf_prefix']
    }
    return render(request, 'transformation/csv_subject.html', html_post_data)


def csv_predicate(request):
    print("VIEW csv_predicate")
    form_action = 5
    form = PredicateForm(request.POST)
    reduced_model = None
    if request.POST and form.is_valid() and form != None:
        # content  is passed on via hidden html input fields
        '''
        if 'hidden_rdf_array_field' in form.cleaned_data:
            request.session['rdf_array'] = form.cleaned_data['hidden_rdf_array_field']

        if 'hidden_rdf_prefix_field' in form.cleaned_data:
            request.session['rdf_prefix'] = form.cleaned_data['hidden_rdf_prefix_field']
        '''
        if 'hidden_model' in form.cleaned_data:
            reduced_model = json.loads(form.cleaned_data['hidden_model'])
            time1 = datetime.datetime.now()
            request.session['model'] = update_model(request.session['model'], reduced_model)
            secs = datetime.datetime.now() - time1
            print("updating model: "+str(secs))

    #csv_rows_selected_columns = get_selected_rows_content(request.session)
    time1 = datetime.datetime.now()
    redu = reduce_model(request.session['model'], 10)
    secs = datetime.datetime.now() - time1
    print("reducing model: "+str(secs))
    html_post_data = {
        'action': form_action,
        'rdfModel': json.dumps(redu),
        #'csvContent': csv_rows_selected_columns,
        #'filename': request.session['file_name'],
        #'rdfArray': request.session['rdf_array'],
	    #'rdfPrefix': request.session['rdf_prefix']
    }
    return render(request, 'transformation/csv_predicate.html', html_post_data)


def csv_object(request):

    '''
    #TEST
    m1 = {'columns':[{'fields':[{'field_num':1,'c':'cccold'},{'field_num':4,'c':'ccc2'}]}]}
    print(">>>>>>>>>>")
    print(m1)
    m2red = {'columns':[{'fields':[{'field_num':1,'c':'cccnew'},{'field_num':3,'c':'cccverynew'}]}]}
    m1 = update_model(m1,m2red)
    print("<<<<<<<<<<")
    print(m1)
    print("<<<<<<<<<<")
    m2red = {'columns':[{'fields':[{'field_num':1,'c':'cccnew'},{'field_num':3,'c':'kkkkkkkkkkkkkkkkkk'}]}]}    
    print(m1)
    '''
    

    print("VIEW csv_object")
    form_action = 6
    form = ObjectForm(request.POST)
    reduced_model = None
    #print(request.POST)
    if request.POST and form.is_valid():# and form != None:
        # content  is passed on via hidden html input fields
        '''
        if 'hidden_rdf_array_field' in form.cleaned_data:
            request.session['rdf_array'] = form.cleaned_data['hidden_rdf_array_field']

        if 'hidden_rdf_prefix_field' in form.cleaned_data:
            request.session['rdf_prefix'] = form.cleaned_data['hidden_rdf_prefix_field']
        '''
        if 'hidden_model' in form.cleaned_data:
            reduced_model = json.loads(form.cleaned_data['hidden_model'])

        else:
            request.session['model'] = ""
            print("N O     M O D E L")
    else:
        print("form not valid!")


    num_rows_model = len(request.session['model']['columns'][0]['fields'])

    #print(request.session['model'])

    #pagination
    if "page" in request.GET and is_int(request.GET.get('page')):
        page = int(request.GET.get('page'))
    else:
        page = 1

    if "num" in request.GET and is_int(request.GET.get('num')):
        perPage = int(request.GET.get('num'))
    else:
        perPage = 10    

    max_pages = num_rows_model // perPage
    if num_rows_model % perPage > 0: #'rest'
        max_pages += 1

    if page > num_rows_model / perPage:
        page = max_pages

    paging_html = ""
    for x in range(max_pages):
        f = (x * perPage) + 1
        t = f + perPage - 1
        if t > num_rows_model:
            t = num_rows_model
        recentPage = ""
        if x+1 == page:
            recentPage = " recent-page"
        paging_html += '<a class="pagination-link'+recentPage+'" href="?page='+str(x+1)+'&num='+str(perPage)+'">'+str(f)+'-'+str(t)+'</a> |'
    paging_html = paging_html[:-2]


    row_num_select = '<select id="select-rows-per-page">'
    pages_arr = [10,25,50,100]
    #insert a page amount in the the if it was modified in the url get params
    if perPage not in pages_arr:
        pages_arr.append(perPage)
    if num_rows_model not in pages_arr:
        pages_arr.append(num_rows_model)
    pages_arr = sorted(pages_arr)
    for p in pages_arr:
        if p <= num_rows_model:
            selected = ""
            if p == perPage:
                selected = " selected"
            row_num_select += "<option"+selected+' href="?page='+str(page)+'&num='+str(p)+'">'+str(p)+"</option>"
    row_num_select += "</select>"

    startRow = page*perPage
    endRow = page*perPage + perPage

    pagination = {
            'startRow': startRow,
            'endRow': endRow,
            'html': paging_html,
            'perPage': perPage,
            'page': page,
            'max_pages': max_pages,
            'num_rows': num_rows_model,
            'row_num_select_html': row_num_select}

    # pagination end

    
    #request.session['model'] = json.loads(form.cleaned_data['hidden_model'])
    #request.session['model'] = 
    #print("v ",len(request.session['model']['columns'][1]['fields']))
    #print("v ",request.session['model']['columns'][1]['fields'])
    #print("r ",len(reduced_model['columns'][1]))
    #print("r ",reduced_model['columns'][1])
    request.session['model'] = update_model(request.session['model'], reduced_model)
    #print("r ",len(reduced_model['columns'][1]['fields']))
    #print("r ",reduced_model['columns'][1]['fields'])
    #print("n ",len(request.session['model']['columns'][1]))
    #print("n ",request.session['model']['columns'][1])
    

    #csv_rows_selected_columns = get_selected_rows_content(request.session)
    html_post_data = {
        'pagination': pagination,
        'action': form_action,
        'rdfModel': json.dumps(reduce_model(request.session['model'], pagination)),
        #'csvContent': csv_rows_selected_columns,
        #'filename': request.session['file_name'],
        #'rdfArray': request.session['rdf_array'],
	    #'rdfPrefix': request.session['rdf_prefix']
    }
    return render(request, 'transformation/csv_object.html', html_post_data)


def is_int(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False


def csv_enrich(request):
    print("VIEW csv_additional")
    form_action = 7
    form = EnrichForm(request.POST)
    reduced_model = None
    if request.POST and form.is_valid() and form != None:
        # content  is passed on via hidden html input fields
        '''
        if 'hidden_rdf_array_field' in form.cleaned_data:
            request.session['rdf_array'] = form.cleaned_data['hidden_rdf_array_field']

        if 'hidden_rdf_prefix_field' in form.cleaned_data:
            request.session['rdf_prefix'] = form.cleaned_data['hidden_rdf_prefix_field']
        '''
        if 'hidden_model' in form.cleaned_data:
            reduced_model = json.loads(form.cleaned_data['hidden_model'])
            request.session['model'] = update_model(request.session['model'], reduced_model)


    #csv_rows_selected_columns = get_selected_rows_content(request.session)
    html_post_data = {
        'action': form_action,
        'rdfModel': json.dumps(reduce_model(request.session['model'], 10)),
        #'csvContent': csv_rows_selected_columns,
        #'filename': request.session['file_name'],
        #'rdfArray': request.session['rdf_array'],
	    #'rdfPrefix': request.session['rdf_prefix']
    }
    return render(request, 'transformation/csv_enrich.html', html_post_data)


def csv_publish(request):
    print("VIEW csv_publish")
    form_action = 7  #refers to itself
    form = PublishForm(request.POST)
    reduced_model = None
    rdf_n3 = "@prefix dbpedia: <http://dbpedia.org/resource> .\n"
    publish_message = ""

    rdf_array = model_to_triples(request.session['model'])

    for row in rdf_array:#ast.literal_eval(request.session['rdf_array']):#['rdf_array']:
        for elem in row:
            elem = elem.replace(",","\\,"); # escape commas
            if elem[-1:] == ".": # cut off as we had problems when uploading some uri like xyz_inc. with trailing dot
                elem = elem[:-1]
            rdf_n3 += elem + " "
        rdf_n3 += ".\n"



    if request.POST and form.is_valid() and form != None:
    #    #if form.cleaned_data['hidden_rdf_array_field']:            
    #    #    request.session['rdf_array'] = form.cleaned_data['hidden_rdf_array_field']
 


        if 'hidden_model' in form.cleaned_data:
            reduced_model = json.loads(form.cleaned_data['hidden_model'])
            request.session['model'] = update_model(request.session['model'], reduced_model)

        if 'button_publish' in request.POST:
            payload = {'title': request.POST.get('name_publish'), 'content': rdf_n3, 'format': 'text/rdf+n3'}
            #Please set the API_HOST in the settings file
            r = requests.post('http://' + API_HOST + '/api/datasource/create/', data=payload)
            j = json.loads(r.text)
            print(j["message"])
            publish_message = j["message"]

        if 'button_download' in request.POST:
            new_fname = request.session['model']['file_name'].rsplit(".", 1)[0]+".n3"
            rdf_string = rdf_n3
            rdf_file = ContentFile(rdf_string.encode('utf-8'))
            response = HttpResponse(rdf_file, 'application/force-download')
            response['Content-Length'] = rdf_file.size
            response['Content-Disposition'] = 'attachment; filename="'+new_fname+'"'
            #print(rdf_n3)
            return response

        if 'button_r2rml' in request.POST:
            new_fname = request.session['model']['file_name'].rsplit(".", 1)[0]+"_R2RML.ttl"
            r2rml_string = transform2r2rml(request.session['model'])
            r2rml_file = ContentFile(r2rml_string.encode('utf-8'))
            response = HttpResponse(r2rml_file, 'application/force-download')
            response['Content-Length'] = r2rml_file.size
            response['Content-Disposition'] = 'attachment; filename="'+new_fname+'"'
            return response

        if 'save_mapping' in request.POST:
            #remove unwanted info from model
            m_light = model_light(request.session['model'])
            transformation_file = ContentFile(json.dumps(m_light).encode('utf-8'))
            mapping = Mapping(user = request.user, fileName = request.POST.get('name_mapping'), csvName = request.session['model']['file_name'])
            mapping.mappingFile.save(request.POST.get('name_mapping'), transformation_file)
            mapping.save()


    #csv_rows_selected_columns = get_selected_rows_content(request.session)
    html_post_data = {
        'publish_message': publish_message,
        'action': form_action,
        'rdfModel': json.dumps(request.session['model']),
        #'csvContent': csv_rows_selected_columns,
        #'filename': request.session['file_name'],
        #'rdfArray': request.session['rdf_array'],
	    #'rdfPrefix': request.session['rdf_prefix']
    }
    return render(request, 'transformation/csv_publish.html', html_post_data)




# ###############################################
#  OTHER FUNCTIONS
# ###############################################


def model_light(model):
    '''
    Delete all field and file specific data, that is keep only data that will be needed when loading csvs of the same structure but containing different content
    '''
    result = copy.deepcopy(model)
    if 'file_name' in result:
        del result['file_name']
    for col in result['columns']:
        if 'fields' in col:
            del col['fields']
        #if 'header' in col:
        #    del col['header']
    return result


def lookup(request, queryClass, queryString, callback):
    headers = {'Accept': 'application/json'}
    r = requests.get(
        'http://lookup.dbpedia.org/api/search/KeywordSearch?QueryClass=' + queryClass + '&QueryString=' + queryString,
        headers=headers)
    text = r.text
    results = json.loads(text)
    return callback + "(" + JsonResponse(results) + ");"


# returns only the contents of the columns that were chosen in the html form from the session data
# for step 2 (column selection)
def get_selected_rows_content(session):
    result = []
    # write column numbers in array
    col_nums = []
    for col_num in session['selected_columns']:
        col_nums.append(col_num.get("col_num_orig"))

    for row in session['csv_rows']:
        tmp_row = []
        for cn in col_nums:
            tmp_row.append(row[cn - 1])
        result.append(tmp_row)
    return result
'''
# marks selected columns directly in model
def mark_selected_rows_in_model(session):
    # write column numbers in array
    col_nums = []
    print(session['selected_columns'])
    for col_num in session['selected_columns']:
        col_nums.append(col_num.get("col_num_orig"))
    session['model']['num_cols_selected'] = len(col_nums)
    counter = 1;
    for i, col in enumerate(session['model']['columns']):
        if col["col_num_orig"] in col_nums:
            col["col_num_new"] = counter
            counter = counter + 1
        else:
            col["col_num_new"] = -1
'''




def process_csv(csvfile, form):
    '''
    Processes the CSV File and converts it to a 2dim array.
    Uses either the CSV Paramaters specified in the HTML form if those exist
    or the autodetected params instead.
    '''
    csv_dialect = {}
    csv_rows = []
    csvfile.seek(0)
    # Sniffer guesses CSV parameters / dialect
    # when error 'could not determine delimiter' -> raise bytes to sniff
    dialect = csv.Sniffer().sniff(csvfile.read(10240))
    csvfile.seek(0)
    # ['delimiter', 'doublequote', 'escapechar', 'lineterminator', 'quotechar', 'quoting', 'skipinitialspace']
    csv_dialect['delimiter'] = dialect.delimiter
    csv_dialect['escape'] = dialect.escapechar
    csv_dialect['quotechar'] = dialect.quotechar
    csv_dialect['line_end'] = dialect.lineterminator.replace('\r', 'cr').replace('\n', 'lf')

    # use csv params / dialect chosen by user if specified
    # to avoid '"delimiter" must be an 1-character string' error, I encoded to utf-8
    # http://stackoverflow.com/questions/11174790/convert-unicode-string-to-byte-string
    if form.cleaned_data['delimiter'] != "":
        dialect.delimiter = form.cleaned_data['delimiter']  #.encode('utf-8')
    if form.cleaned_data['escape'] != "":
        dialect.escapechar = form.cleaned_data['escape']  #.encode('utf-8')
    if form.cleaned_data['quotechar'] != "":
        dialect.quotechar = form.cleaned_data['quotechar']  #.encode('utf-8')
    if form.cleaned_data['line_end'] != "":
        dialect.lineterminator = form.cleaned_data['line_end']  #.encode('utf-8')

    csvreader = csv.reader(csvfile, dialect)



    for row in csvreader:
        csv_rows.append(row)

    #removal of blanks, especially special blanks \xA0 etc.
    for i,rowa in enumerate(csv_rows):
        for j,field in enumerate(rowa):
            csv_rows[i][j] = field.strip()

    return [csv_rows, csv_dialect]

def transform2r2rml(jsonmodel):
    #head = json.load(jsonmodel)

    subject = jsonmodel["subject"]
    columns = jsonmodel["columns"]
    ourprefix = "demo"
    subjtypes = []
    output = ""

    if "enrich" in jsonmodel:
        for enr in jsonmodel["enrich"]:
            subjtypes.append(enr["url"])

    output = "@prefix rr: <http://www.w3.org/ns/r2rml#>.\n" \
             "@prefix " + ourprefix + ": <" + subject["base_url"] + ">.\n\n" + ourprefix + ":TriplesMap a rr:TriplesMapClass;\n" \
                "\trr:logicalTable [ rr:tableName \"" + jsonmodel["file_name"] + "\" ];\n\n\trr:subjectMap [ rr:template \"" + \
             subject["base_url"] + subject["skeleton"] + "\""

    for sutp in subjtypes:
        output += ";\n\t\trr:class " + sutp

    output += "\n\t];  # of columns selected: " + str(jsonmodel["num_cols_selected"])

    for column in columns:
        if (column["col_num_new"] >= 0) and ("predicate" in column):
            predicate = column["predicate"]
            header = column["header"]
            output += ";\n\trr:predicateObjectMap [\n\t\trr:predicateMap [ rr:predicate " + predicate["url"] + " ];\n\t\t" \
                        "rr:ObjectMap [ rr:column \"" + header["orig_val"] + "\" ]\n\t]"

    output += "."

    return output




def update_model(model, reduced_model):
    '''
    Takes a model and updates it with reduced model
    '''
    # fields
    m = copy.deepcopy(model)
    for i, col in enumerate(m['columns']):
        exists = -1
        for j, field in enumerate(reduced_model['columns'][i]['fields']):

            #for performance when paginating
            if exists == -1:
                rnge = range(0,len(model['columns'][i]['fields']))
            else:
                rnge = chain(range(exists, len(model['columns'][i]['fields'])), range(0, exists))

            #fields
            #for k, col_red in enumerate(model['columns'][i]['fields']):
            for k in rnge:
                if reduced_model['columns'][i]['fields'][j]['field_num'] == m['columns'][i]['fields'][k]['field_num']:
                    m['columns'][i]['fields'][k] = reduced_model['columns'][i]['fields'][j].copy()
                    #print("OVERWRiTING ", m['columns'][i]['fields'][j], "  ",reduced_model['columns'][i]['fields'][k])
                    exists = k
                    break
            if exists == -1:
                m['columns'][i]['fields'].append(reduced_model['columns'][i]['fields'][j].copy())
                #print("ADDING")
            # sort
            newlist = sorted(m['columns'][i]['fields'].copy(), key=lambda k: k['field_num'])
            m['columns'][i]['fields'] = newlist

        #predicate
        if 'predicate' in reduced_model['columns'][i]:
            col['predicate'] = copy.deepcopy(reduced_model['columns'][i]['predicate'])

        #column choice
        if 'col_num_new' in reduced_model['columns'][i]:
            col['col_num_new'] = copy.deepcopy(reduced_model['columns'][i]['col_num_new'])

        #header
        if 'header' in reduced_model['columns'][i]:
            col['header'] = copy.deepcopy(reduced_model['columns'][i]['header'])

        #object_method
        if 'object_method' in reduced_model['columns'][i]:
            col['object_method'] = copy.deepcopy(reduced_model['columns'][i]['object_method'])

        #data_type
        if 'data_type' in reduced_model['columns'][i]:
            col['data_type'] = copy.deepcopy(reduced_model['columns'][i]['data_type'])

    #subject
    if 'subject' in reduced_model:
        m['subject'] = copy.deepcopy(reduced_model['subject'])

    #enrich
    if 'enrich' in reduced_model:
        m['enrich'] = copy.deepcopy(reduced_model['enrich'])

    #file_name
    if 'file_name' in reduced_model:
        m['file_name'] = copy.deepcopy(reduced_model['file_name'])



    return m


def reduce_model(model, pagination):
    '''
    pagination can be 
    int number: first x elements will be selected
    dict of 'pagination', with page and perPage attributes as in views.py -> csv_object function
    '''
    reduced_model = copy.deepcopy(model)

    #print("reduced_model")
    #printfields(reduced_model)

    num_rows = reduced_model['num_cols_selected']
    p = False
    f = 0
    if isinstance(pagination, dict) and 'page' in pagination and 'perPage' in pagination:
        p = True
        f = (pagination['page']-1) * pagination['perPage']
        t = f + pagination['perPage']
    for i, col in enumerate(reduced_model['columns']):
        if not 'col_num_new' in col or col['col_num_new'] > -1: #show column

            if p:
                fields = reduced_model['columns'][i]['fields'][f:t].copy()
            elif isinstance(pagination, int):
                fields = reduced_model['columns'][i]['fields'][:pagination].copy()
            else:
                fields = reduced_model['columns'][i]['fields'].copy()

            reduced_model['columns'][i]['fields'] = fields

        else: # remove columns that are not selected
            reduced_model['columns'][i]['fields'] = []
    return reduced_model


def printfields(model):
    '''
    for debugging purposes
    '''
    for c in model['columns']:
        if 'fields' in c:
            print(str(len(c['fields']))," FIELDS YES in ",c['header']['orig_val'])
        else:
            print("FIELDS NOO in ",c['header']['orig_val'])

def print_model_dim(model):
    '''
    for debugging purposes
    '''
    print("model dim: ",len(model['columns']), " x ", len(model['columns'][0]['fields']))

'''
def create_subjects_from_model_skeleton(model):
    skeleton = ""
    base_url = ""

    skeleton = model['subject']['skeleton'];
    base_url = model['subject']['base_url'];

    if not skeleton and not base_url:
        skeleton = "?subject?"

    subjects_array = []
    for i,col in enumerate(model['columns']):
        if col['col_num_new'] >- 1: # column was chosen, same as show==true
            col_name = col['header']['orig_val']
            for j,elem in enumerate(col['fields']):
                #if model['subject']['blank_nodes'] == "true"):
                #        subjects_array[j] = "_:"+toLetters(j+1);
                #else:
                if subjects_array[j] == undefined:
                    subjects_array[j] = "<" + base_url.trim() + skeleton.trim() + ">"                    
                subjects_array[j] = subjects_array[j].replace("{"+col_name.trim()+"}", elem['orig_val'].trim()).trim();    

    return subjects_array;
'''

def model_to_triples(model):

    num_fields_in_row_rdf = len(model['columns'][0]['fields'])
    num_total_cols = 0

    #count
    for col in model['columns']:
        if col['col_num_new'] >- 1:
            num_total_cols += 1

    num_total_fields_rdf = num_fields_in_row_rdf * num_total_cols


    print_model_dim(model)
    print(num_total_cols, " cols")

    skeleton = model['subject']['skeleton']
    base_url = model['subject']['base_url']

    subject = "<?s>"
    if skeleton != "" and base_url != "":
        subject = base_url+skeleton

    #contains names that are needed for subject creation
    skeleton_array = re.findall("\{(.*?)\}",skeleton)
    skeleton_array_ids = [x for x in range(0,len(skeleton_array))]
    print("sekl: ", skeleton_array)
    for i,col in enumerate(model['columns']):
        for j,skel in enumerate(skeleton_array):
            if col['header']['orig_val'] == skel:
                skeleton_array_ids[j] = i
                break

    print("sekl: ", skeleton_array_ids)



    rdf_array = [[subject,"<?p>","<?o>"] for x in range(0,num_total_fields_rdf)]

    print(len(rdf_array)," x ",len(rdf_array[0]))

    prefix_dict = {}

    #objects
    count1 = 0    
    for i,col in enumerate(model['columns']):
        if col['col_num_new'] >- 1:
            count2 = count1 
            add = ""
            if 'object_method' in col and col['object_method'] == "data type":
                add = "^^"+col['data_type']['suffix']
                prefix_dict[col['data_type']['prefix']] = col['data_type']['suffix']   
            for j,field in enumerate(col['fields']):  
                if 'object_method' in col and col['object_method'] == "reconciliation" and 'reconciliation' in field:
                    rdf_array[count2][2] = field['reconciliation']['prefix']['prefix']+":"+field['reconciliation']['prefix']['suffix']
                else:
                    rdf_array[count2][2] = '"'+field['orig_val']+'"'+add
                count2 += num_total_cols
        count1 += 1


    #subjects
    for i,s in enumerate(skeleton_array):
        counter = 0
        for field in model['columns'][i]['fields']:
            pass
            print(field)
            for x in range(counter, counter+num_total_cols):
                rdf_array[x][0] = rdf_array[x][0].replace("{"+skeleton_array[i]+"}",field['orig_val'])
            counter += num_total_cols


    #predicates
    for i,col in enumerate(model['columns']):
        if col['col_num_new'] >- 1:
            url = col['predicate']['prefix']['url']
            prefix = col['predicate']['prefix']['prefix']
            suffix = col['predicate']['prefix']['suffix']            
            if prefix == "" or suffix == "":
                u = url
            else:
                u = prefix+":"+suffix
                prefix_dict[prefix] = url
            #count2 = i
            for x in range(0, num_fields_in_row_rdf):
                rdf_array[i+x*num_total_cols][1] = u
                #count2 += num_fields_in_row_rdf

    #enrich
    enrich_array = []
    for enr in model['enrich']:
        enrich_array.append(["<subject?>","a",enr['prefix']['prefix']+":"+enr['prefix']['suffix']])

    enrichs_inserted = 0
    for n in range(num_total_cols-1,len(rdf_array)+num_total_cols-1,num_total_cols):
        for enr in enrich_array:
            print(enr)
            x = n+enrichs_inserted+1
            rdf_array.insert(x, enr.copy())
            rdf_array[x][0] = rdf_array[x-1][0]
            enrichs_inserted += 1


    prefix_array = []
    for x in prefix_dict:
        prefix_array.append(["@prefix", x+":", "<"+prefix_dict[x]+">"])




    return prefix_array + rdf_array
