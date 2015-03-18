from django.http import HttpResponseRedirect
from django.shortcuts import render, render_to_response
from django.template import RequestContext
from .forms import UploadFileForm
from django.core.urlresolvers import reverse
#import operator


def csv_view(request):
    print("CSV")
    if request.method == 'POST':
        # handle the uploaded file here
        raise


def index(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            print(reverse('transformation-index'))
            csvChunks = []
            csvLines = []
            rows = []
            for chunk in request.FILES['file'].chunks():
                #print(chunk)
                csvChunks.append(chunk)
            
            # SEPARATOR DETECTION
            separator = ","
            if len(csvChunks) > 0:
                #check which separator occurs the most
                separators = {',': 0, ';': 0, '\t': 0, ':': 0}
                for key in separators:
                    separators[key] = csvChunks[0].count(key)
                separator = max(separators, key=separators.get)
                csvLines = csvChunks[0].split("\n", 10)

            if len(csvLines) > 0:
                # pop last item from array as it contains the 'rest' that wasn't split by the split function
                csvLines.pop(len(csvLines)-1)
                for line in csvLines:
                    rows.append(line.split(separator))
            #return render(request, reverse('transformation-index'), {'form': form, 'csvContent': rows})
            return render(request, 'transformation/index.html', {'form': form, 'csvContent': rows, 'separator': separator})
    else:
        form = UploadFileForm()
    return render_to_response('transformation/index.html', {'form': form}, context_instance=RequestContext(request))
