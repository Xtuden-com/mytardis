from django.template import Context
from django.http import HttpResponse
from django.views.decorators.cache import never_cache

from tardis.tardis_portal.auth import decorators as authz
from tardis.tardis_portal.shortcuts import render_response_index
from tardis.tardis_portal.views import *

from tardis.tardis_portal.models import DatafileParameterSet
from tardis.tardis_portal.models import Schema
    
def index_mt(request):
    status = ''

    c = Context({'status': status})
    return HttpResponse(render_response_index(request,
                        'index_mt.html', c))

def about_mt(request):
    c = Context({'subtitle': 'About',
                 'about_pressed': True,
                 'nav': [{'name': 'About', 'link': '/about/'}]})
    
    return HttpResponse(render_response_index(request,
                        'about_mt.html', c))
    
def partners_mt(request):
    c = Context({})
    
    return HttpResponse(render_response_index(request,
                        'partners_mt.html', c))
    
@never_cache
@authz.datafile_access_required
def retrieve_parameters(request, dataset_file_id):
    schema_edaxgenesis_spc = Schema.objects.filter(name="EDAXGenesis_SPC")
    schema_id = 0
    if schema_edaxgenesis_spc:
        schema_id = schema_edaxgenesis_spc[0].id
    ordered_fields = ["Sample Type (Label)", "Preset", "Live Time", "Acc. Voltage"]
    datafileparametersets = DatafileParameterSet.objects.filter(dataset_file__pk=dataset_file_id)
    parametersets = {}
    for parameterset in datafileparametersets:
        if parameterset.schema.id == schema_id:
            unsorted = {}
            sorted = []
            for parameter in parameterset.datafileparameter_set.all():
                unsorted[str(parameter.name.full_name)] = parameter
            for field in ordered_fields:
                if field in unsorted:
                    sorted.append(unsorted[field])
                    unsorted.pop(field)
            if unsorted:
                sorted_keys = unsorted.keys()
                sorted_keys.sort()
                for key in sorted_keys:
                    sorted.append(unsorted[key])
            parametersets["%s" % (parameterset.schema)] = sorted
            
        else:
            parametersets["%s" % (parameterset.schema)] = parameterset.datafileparameter_set.all

    c = Context({'parametersets': parametersets})

    return HttpResponse(render_response_index(request,
                        'parameters_mt.html', c))