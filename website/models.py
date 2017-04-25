from django.db import models
from ckeditor.fields import RichTextField
from django.utils.text import slugify


class Person(models.Model):
    first = models.CharField(max_length=80, blank=True)
    middle_initials = models.CharField(max_length=80, blank=True)
    last = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return ' '.join([self.first, self.middle_initials, self.last])

    class Meta:
        ordering = ['first', 'last']
        verbose_name_plural = "people"


class Reference(models.Model):
    """A generic reference type which links to journal articles, books, etc."""
    title = models.CharField(max_length=400, null=True, blank=True)
    authors = models.ManyToManyField(Person, blank=True, through='Authorship')
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    doi = models.CharField(max_length=500, blank=True, null=True)

    bibtex = models.TextField()

    def __str__(self):
        return self.title + ' (' + str(self.year) + ')' + ' Authors: ' + ', '.join(str(a) for a in self.authors.all())


class Authorship(models.Model):
    person = models.ForeignKey(Person)
    reference = models.ForeignKey(Reference)
    weight = models.PositiveIntegerField(default=0)


class Threat(models.Model):
    name = models.CharField(max_length=300, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Habitat(models.Model):
    name = models.CharField(max_length=300, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Assessment(models.Model):
    pass


class Criteria(models.Model):
    pass


class Species(models.Model):
    scientific_name = models.CharField(max_length=150, unique=True, help_text="E.g. Eudyptes moseleyi")
    common_name = models.CharField(max_length=150, help_text="List multiple common names separated by commas")
    family = models.CharField(max_length=150, blank=True, help_text="E.g. Spheniscidae")
    author = models.CharField(max_length=150, blank=True, help_text="E.g. (Smith A, 1834)")

    regional_status_2015 = models.CharField(max_length=80, blank=True, help_text="E.g. Critically Endangered* [C1]")
    regional_status_2010 = models.CharField(max_length=80, blank=True, help_text="E.g. Critically Endangered [A2bcd+3bc+4bcd]")
    regional_status_2000 = models.CharField(max_length=80, blank=True, help_text="E.g. Vulnerable [C1]")
    global_status_2015 = models.CharField(max_length=80, blank=True, help_text="E.g. Critically Endangered [A2bcd+3bc+4bd]")
    status_change_reason = models.CharField(max_length=150, blank=True, help_text="E.g. Application of criteria")

    population_size = models.CharField(max_length=80, blank=True, help_text="Enter description, e.g. c. 160 mature individuals (80 breeding pairs)")
    distribution_size = models.CharField(max_length=80, blank=True, help_text="Enter description, e.g. 33 522 km2")
    regional_endemic = models.CharField(max_length=50, blank=True, help_text="Yes, No or Partial")

    conservation_underway = RichTextField()
    conservation_proposed = RichTextField()
    distribution = RichTextField()
    ecology = RichTextField()
    identification = RichTextField()
    justification = RichTextField()
    population_justification = RichTextField()
    population_trend_justification = RichTextField()
    inclusion_reason = RichTextField()
    taxonomy = RichTextField()
    threats_narrative = RichTextField()

    threats = models.ManyToManyField(Threat, blank=True, help_text="<strong>Start typing to search through options.</strong> ")
    habitats = models.ManyToManyField(Habitat, blank=True, help_text="<strong>Start typing to search through options.</strong> ")
    references = models.ManyToManyField(Reference, blank=True, help_text="<strong>Start typing to search through options. Click the green plus sign to add a new reference. </strong> ")

    research_priorities = RichTextField()

    contributors = models.ManyToManyField(Person, through='Contribution')
    slug = models.SlugField(unique=True, editable=False, blank=True)
    created_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        #if not self.id:
        self.slug = slugify(self.scientific_name)

        return super(Species, self).save(*args, **kwargs)

    def __str__(self):
        return self.scientific_name + ' (' + self.common_name + ')'

    class Meta:
        verbose_name_plural = "species"
        ordering = ['scientific_name']


class Contribution(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    weight = models.PositiveSmallIntegerField()
    ASSESSOR = 'A'
    REVIEWER = 'R'
    TYPE_CHOICES = (
        (ASSESSOR, 'Assessor'),
        (REVIEWER, 'Reviewer'),
    )
    type = models.CharField(max_length=1, choices=TYPE_CHOICES)

