"""redlist URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from website import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', views.Index.as_view(), name='index'),
    url(r'^export/$', views.export_data, name='export'),
    url(r'^import/$', views.import_data, name='import'),
    url(r'^import/bibtex/$', views.import_refs, name='import_refs'),
    url(r'^split/$', views.split_data, name='split'),
    url(r'^bird/(?P<slug>[\w-]+)/$', views.SpeciesDetail.as_view(), name='species_detail'),  # (?P<pk>[0-9]+)
    url(r'^contributor/(?P<pk>[0-9]+)/$', views.SpeciesDetail.as_view(), name='contributor'),
]
