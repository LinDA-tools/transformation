from django.http import HttpResponseRedirect
from django.shortcuts import render, render_to_response
from django.template import RequestContext
from .forms import UploadFileForm
from django.core.urlresolvers import reverse
#import operator


def index(request):
    print("CSV")
    if request.method == 'POST':
        # handle the uploaded file here
        raise


def csv_upload(request):
    if request.method == 'POST':
        print('  --  POST  --  ')
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            csvChunks = []
            csvLines = []
            rows = []
            print('file:')
            print(request.FILES)
            for chunk in request.FILES['file'].chunks():
                print(chunk)
                csvChunks.append(chunk)
            
            # separator_proposal DETECTION
            separator_proposal = None
            if len(csvChunks) > 0:
                #check which separator_proposal occurs the most
                separators = {',': 0, ';': 0, '\t': 0, ':': 0}
                for key in separators:
                    separators[key] = csvChunks[0].count(key)
                separator_proposal = max(separators, key=separators.get)
                csvLines = csvChunks[0].split("\n", 10)

            if len(csvLines) > 0:
                # pop last item from array as it contains the 'rest' that wasn't split by the split function
                csvLines.pop(len(csvLines)-1)
                for line in csvLines:
                    rows.append(line.split(separator_proposal))
            #return render(request, reverse('csv-upload-view'), {'form': form, 'csvContent': rows, 'separator_proposal': separator_proposal})
            #return render(request, 'transformation/csv_upload.html', {'form': form, 'csvContent': rows, 'separator_proposal': separator_proposal})
            return render_to_response('transformation/csv_upload.html', {'form': form, 'csvContent': rows, 'separator_proposal': separator_proposal}, context_instance=RequestContext(request))
        else:
            print('form not valid')
            print form.errors
    else:
        print('Form not valid!')
        form = UploadFileForm()
    return render_to_response('transformation/csv_upload.html', {'form': form}, context_instance=RequestContext(request))
