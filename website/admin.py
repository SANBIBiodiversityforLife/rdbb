from django import forms
from django.contrib import admin
from website import models
from ckeditor.widgets import CKEditorWidget

'''
class SpeciesAdminForm(forms.ModelForm):
	conservation_underway = forms.TextField(widget=CKEditorWidget())
	
	class Meta:
		model = models.Species
		

class SpeciesAdmin(admin.ModelAdmin):
	form = SpeciesAdminForm

admin.site.register(models.Species, SpeciesAdmin)'''


class ContributionInline(admin.TabularInline):
    model = models.Contribution
    extra = 1


class SpeciesAdmin(admin.ModelAdmin):
    inlines = (ContributionInline, )

    class Media:
        # Put your jquery up first (automatically included but it appears below the chosen.jquery.min.js, adding it again just seems to shift it above
        js = ('//ajax.googleapis.com/ajax/libs/jquery/2.1.1/jquery.min.js',
              #'https://cdnjs.cloudflare.com/ajax/libs/chosen/1.6.2/chosen.jquery.min.js', Use a cdn if you prefer
              'chosen/chosen.jquery.min.js',
              'chosen_admin.js')
        css = {'all': ('chosen/chosen.min.css','chosen_admin.css',
                       #'https://cdnjs.cloudflare.com/ajax/libs/chosen/1.6.2/chosen.min.css'
                       )}

admin.site.register(models.Species, SpeciesAdmin)
admin.site.register(models.Person)
admin.site.register(models.Reference)
