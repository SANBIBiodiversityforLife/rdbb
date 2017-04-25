from django.shortcuts import render
from bs4 import BeautifulSoup
from website import models
import redlist.settings as settings
import os
from django.views.generic.list import ListView
from django.views.generic import DetailView
import json
import requests
import time
import re
import datetime
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

class SpeciesDetail(DetailView):
    model = models.Species
    context_object_name = 'bird'


class Index(ListView):
    model = models.Species
    context_object_name = 'birds'

    
def get_reference_parts(authority):
    # Splits up an authority string formatted in the standard way e.g. (Barnard, 1937) into year and author
    bracketed = '(' in authority
    authority = re.sub('[()]', '', authority)
    authority = authority.split(',')
    year = authority[-1].strip()
    authors = authority[0]
    author_list = []
    for surname in authors.split('&'):
        author = get_or_create_author(surname=surname)
        author_list.append(author)
    
    
def get_api_info(api_url):
    time_delay = 0
    r = False
    while not r:
        try:
            time.sleep(time_delay)
            r = requests.get(api_url)
        except ConnectionError:
            # Add 5 seconds onto the time delay
            time_delay += 15
            # Print out so we can monitor it
            print('Timed out, trying again in ' + time_delay + ' seconds')
    return r    

    
def create_authors(author_string):
    """
    Splits up an author string formatted as e.g. Braack, H.H. and Bishop, P.J. and Knoepfer, D.
    Creates Person objects for each, and returns them in a list
    :param author_string:
    :return:
    """
    # Remove the 'and' so that we can apply a simple regex to split up the authors
    author_list = author_string.split(' and ')
    people = []
    for author in author_list:
        name_parts = author.split(',')
        if len(name_parts) != 2:
            surname = name_parts[0].strip()
            initials = ''
        else: 
            surname = name_parts[0].strip()
            initials = name_parts[1].strip()

        # Try and get all possible people in the database first
        p = models.Person.objects.filter(last=surname, middle_initials=initials).first()

        # If there's nobody there then try get same surname and no initials, it's probably the same person
        # Someone can split it out later manually if it's not
        if p is None:
            p = models.Person.objects.filter(last=surname, middle_initials__isnull=True, middle_initials__exact='').first()
            if p is None:
                # Otherwise if we can't find anyone with the same surname make a new person
                p = models.Person(last=surname, middle_initials=initials)
            else:
                p.middle_initials = initials
            p.save()

        people.append(p)
    return people

    

def import_refs(request):
    file_url = os.path.join(settings.BASE_DIR, 'bibtex-for-import.txt')
    with open(file_url, 'r', encoding='utf-8') as bibtex_file:
        bibtex_str = bibtex_file.read()
        bib_db = bibtexparser.loads(bibtex_str)
        empty_db = BibDatabase()
        writer = BibTexWriter()
        for bib_entry in bib_db.entries:
            if 'title' not in bib_entry or 'year' not in bib_entry or 'author' not in bib_entry or len(bib_entry['year']) > 4:
                continue
            empty_db.entries = [bib_entry]
            bibtex = writer.write(empty_db)
            ref, created = models.Reference.objects.get_or_create(bibtex=bibtex, year=bib_entry['year'], title=bib_entry['title'])
            author_list = create_authors(bib_entry['author'])
            for author in author_list:
                authorship = models.Authorship(reference=ref, person=author)
                authorship.save()
            # import pdb; pdb.set_trace()


def export_data(request):
    redlist_cat_mapping = {
        'regionally extinct': 'EX',
        'critically endangered': 'CR',
        'endangered': 'EN',
        'vulnerable': 'VU',
        'near threatened': 'NT',
        'least concern': 'LC',
        'data deficient': 'DD',
        'not listed': 'NE',
        'not set': 'NE',
    }
    chordata = 6 # ALERT! Hardcoding! CHANGE THIS!
    english = 1
    
    # Get list of ranks from input db
    base_url = 'http://172.16.6.250:8000/'
    ranks = requests.get(base_url + 'taxa/api/rank-list/?format=json').json()
    ranks = {r['name']: r['id'] for r in ranks['results']}

    gbif_url = 'http://api.gbif.org/v1/species?name='
    create_taxon_api = base_url + 'taxa/api/taxon-write/?format=json'
    create_descrip_api = base_url + 'taxa/api/description-format-write/?format=json'
    create_info_api = base_url + 'taxa/api/info-write/?format=json'
    create_ass_api = base_url + 'assessment/api/assessment-write/?format=json'
    create_contrib_api = base_url + 'assessment/api/contribution-write/?format=json'
    create_person_api = base_url + 'api/people/?format=json'
    create_cn_api =  base_url + 'taxa/api/cn-write/?format=json'
    create_ref_api =  base_url + 'biblio/api/post-bibtex/?format=json'
    sps = models.Species.objects.all()
        
    aves = {'name': 'Aves', 'parent': chordata, 'rank': ranks['Class']}
    r_aves = requests.post(create_taxon_api, data=aves)
    print(r_aves)
    r_aves_cn = requests.post(create_cn_api, data={'name': 'Birds', 'language': english, 'taxon': r_aves.json()['id']})
    print(r_aves_cn)
    r_aves_id = r_aves.json()['id']
    
    for sp in sps:                 
        # Get taxa info from gbif
        r = get_api_info(gbif_url + sp.scientific_name)
        results = r.json()['results']
        if len(results) < 1:
            if sp.scientific_name == 'Camphetera notata':
                top_result = {'order': 'Piciformes', 'genus': 'Campethera'}
            else: 
                import pdb; pdb.set_trace()
        else: 
            top_result = results[0]
        
        order = {'name': top_result['order'], 'parent': r_aves_id, 'rank': ranks['Order']}
        r_order = requests.post(create_taxon_api, data=order)
        print(r_order)
        
        family = {'name': sp.family, 'parent': r_order.json()['id'], 'rank': ranks['Family']}
        r_family = requests.post(create_taxon_api, data=order)
        print(r_family)
        
        genus = {'name': top_result['genus'], 'parent': r_family.json()['id'], 'rank': ranks['Genus']}
        r_genus = requests.post(create_taxon_api, data=genus)
        print(r_genus)
        
        species = {'name': sp.scientific_name, 'parent': r_genus.json()['id'], 'rank': ranks['Species'], 'notes': sp.taxonomy}
        r_species = requests.post(create_taxon_api, data=species)
        sp_id = r_species.json()['id']
        print(r_species)
        r_sp_cn = requests.post(create_cn_api, data={'name': sp.common_name, 'language': english, 'taxon': r_species.json()['id']})
        print(r_sp_cn)
        
        descrip = requests.post(create_descrip_api, data={'author_string': sp.author, 'taxon_pk': sp_id})
        print(descrip)
        
        info = {'taxon': sp_id, 'trophic': sp.ecology, 'diagnostics': sp.identification}
        info = requests.post(create_info_api, data=info)
        print(info)
        # Not yet populated threats  habitats references
        
        assessment = {'taxon': sp_id, 'scope': 'N', 'date': datetime.date(2015, 1, 1), 
                      'population_trend_narrative': sp.population_trend_justification, 'population_narrative': sp.population_justification,
                      'rationale': sp.justification, 'distribution_narrative': sp.distribution, 'notes': sp.inclusion_reason, 
                      'threats_narrative': sp.threats_narrative, 'change_rationale': sp.status_change_reason}
        
        match = re.match(r'^([a-z]+\s*[a-z]*)\s*\*?\s*\[([^\]]+)\]$', sp.regional_status_2015, re.IGNORECASE)
        if match:  
            assessment['redlist_category'] = redlist_cat_mapping[match.group(1).lower().strip()]
            assessment['redlist_criteria'] = match.group(2)
        else:
            print(match)
            import pdb; pdb.set_trace()
        assessment['conservation_narrative'] = '<h4>Underway</h4>' + sp.conservation_underway + '<h4>Proposed</h4>' + sp.conservation_proposed
        assessment['research_narrative'] = sp.research_priorities
        assessment['temp_field'] = {'Population size': sp.population_size, 'Distribution size': sp.distribution_size, 'Regional endemic': sp.regional_endemic}
        ass = requests.post(create_ass_api, data=assessment)
        print(ass)
        
        for contrib in sp.contribution_set.all():
            person = {'first': contrib.person.first, 'surname': contrib.person.last, 'initials': contrib.person.middle_initials}
            person = requests.post(create_person_api, data=person)
            contrib = requests.post(create_contrib_api, data={'person': person.json()['id'], 'type': contrib.type, 'weight': contrib.weight, 'assessment': ass.json()['id']})
            print(contrib)
        
        for reference in sp.references.all():
            #authors = []
            #for person in reference.authors:
            #    person = {'first': person.first, 'surname': person.last, 'initials': person.middle_initials}
            #    person = requests.post(create_person_api, data=person)
            requests.post(create_ref_api, data={'assessment_id': ass.json()['id'], 'bibtex': reference.bibtex})            
        
        #if not ass.ok or not contrib.ok or not info.ok or not descrip.ok or not r_sp_cn.ok or not r_species.ok or not r_family.ok or not r_genus.ok or not r_order.ok:
        #    import pdb; pdb.set_trace()
        #export = {'name': 
    

def split_data(request):
    file_url = os.path.join(settings.BASE_DIR, 'habitats.txt')
    with open(file_url, 'r', encoding='utf-8') as f:
        content = f.readlines()

    for c in content:
        models.Habitat.objects.get_or_create(name=c.strip())

    file_url = os.path.join(settings.BASE_DIR, 'threats.txt')
    with open(file_url, 'r', encoding='utf-8') as f:
        content = f.readlines()

    for c in content:
        models.Threat.objects.get_or_create(name=c.strip())



    return

    def get_or_create_person_from_name(name):
        names = val.split(' ')
        person_args = {'first': names[0].strip(), 'last': names[-1]}
        if len(names) > 2:
            person_args['middle_initials'] = names[1]
        return models.Person.objects.get_or_create(**person_args)

    birds = models.Species.objects.all()
    models.Person.objects.all().delete()

    for bird in birds:
        # Remove all previously set
        bird.contributors.clear()

        # Remove whitespace duplicates
        bird.assessor = ' '.join(bird.assessor.split())
        bird.reviewer = ' '.join(bird.reviewer.split())

        # Fix the concatenation problem
        bird.assessor = bird.assessor.replace(' and ', ',')
        bird.assessor = bird.assessor.replace(', ', ',')
        bird.reviewer = bird.reviewer.replace(' and ', ',')
        bird.reviewer = bird.reviewer.replace(', ', ',')

        # Iterate over the assessors and create them if necessary
        assessors = bird.assessor.split(',')
        for idx, val in enumerate(assessors):
            person, created = get_or_create_person_from_name(val.split(' '))
            c = models.Contribution(person=person, species=bird, weight=idx, type=models.Contribution.ASSESSOR)
            c.save()

        # Iterate over the reviewers and create them if necessary
        reviewers = bird.reviewer.split(',')
        for idx, val in enumerate(reviewers):
            person, created = get_or_create_person_from_name(val.split(' '))
            c = models.Contribution(person=person, species=bird, weight=idx, type=models.Contribution.REVIEWER)
            c.save()

        # Save the bird!
        bird.save()

    import pdb; pdb.set_trace()

    
def import_data(request):
    file_url = os.path.join(settings.BASE_DIR, 'book.html')
    #f = open(file_url, 'r', encoding='latin-1')
    f = open(file_url, 'r', encoding='utf-8')
    html = f.read()
    f.close()

    # Soupify
    soup = BeautifulSoup(html)
    soup.encode('utf-8')

    # Birds list
    birds = []
    facts_titles_list = []

    # Retrieve all divs once and populate birds with their names. We have to do this to start as everything is jumbled
    divs = soup.find_all('div')
    for div in divs:
        ps = div.select('p')
        hs = div.select('h3')

        if len(ps) == 2 and len(hs) == 0:
            if div.has_attr('class') and 'redcredits' not in div['class']:
                bird = models.Species(scientific_name=ps[1].text.strip(), common_name=ps[0].text.strip())
                birds.append(bird)

        # Get small grey block fact titles
        if len(ps) > 5 and ps[0].text.strip().lower() == '2015 regional status':
            fact = []
            for p in ps:
                fact.append(p.text.strip().lower())
                facts_titles_list.append(fact)

    # Small grey block fact text must be matched up to headings
    counter = 0
    for div in divs:
        ps = div.select('p')
        hs = div.select('h3')

        # Get facts to go with fact titles
        # ps[0].text.strip()[-1:] == ']'
        if len(ps) > 4 \
                and len(hs) == 0 \
                and ps[0].text.strip().lower() != 'research priorities and questions' \
                and ps[0].text.strip().lower() != '2015 regional status' \
                and ps[0].text.strip().lower() != 'justification'\
                and len(ps[0].text.strip().split(' ')) < 15:
            print(counter)
            try:
                bird = birds[counter]
                for j, title in enumerate(facts_titles_list[counter]):
                    t = ps[j].text.strip(' ')
                    if title == '2015 regional status':
                        bird.regional_status_2015 = t
                    elif title == '2010 regional status':
                        bird.regional_status_2010 = t
                    elif title == '2000 regional status':
                        bird.regional_status_2000 = t
                    elif title == '2015 global status':
                        bird.global_status_2015 = t
                    elif title == 'status change reason':
                        bird.status_change_reason = t
                    elif title == 'family name':
                        bird.family = t
                    elif title == 'species name author':
                        bird.author = t
                    elif title == 'population size':
                        bird.population_size = t
                    elif title == 'distribution size (aoo)':
                        bird.distribution_size = t
                    elif title == 'regional endemic':
                        bird.regional_endemic = t
                    else:
                        print(title + ' not found, value = ' + t)

                counter += 1
            except IndexError:
                print(len(ps))
                print(len(facts_titles_list[counter]))
                import pdb
                pdb.set_trace()

    # Main body of text
    counter = 0
    for div in divs:
        hs = div.select('h2')
        # Check to make sure we're in the right div, it must have h2s
        if len(hs) > 0:
            # Load the bird we're on
            bird = birds[counter]

            # For each of the tags...
            current_heading = None
            contents = ''

            for tag in div.children:
                # We have reached a new heading! Time to put the content in and move on
                if tag.name == 'h2':
                    if current_heading is None:
                        pass
                    elif current_heading == 'conservation measures underway':
                        bird.conservation_underway = contents
                    elif current_heading == 'distribution':
                        bird.distribution = contents
                    elif current_heading == 'ecology':
                        bird.ecology = contents
                    elif current_heading == 'identification':
                        bird.identification = contents
                    elif current_heading == 'justification':
                        bird.justification = contents
                    elif current_heading == 'population justification':
                        bird.population_justification = contents
                    elif current_heading == 'reason for inclusion in the assessment' or current_heading == 'reasons for inclusion in the assessment':
                        bird.inclusion_reason = contents
                    elif current_heading == 'taxonomy':
                        bird.taxonomy = contents
                    elif current_heading == 'threats':
                        bird.threats = contents
                    elif current_heading == 'trend justification' or current_heading == 'population trend justification':
                        bird.population_trend_justification = contents
                    else:
                        print('Unknown h2 ' + tag.text)
                        import pdb; pdb.set_trace()

                    # Reset heading and contents
                    current_heading = tag.text.strip().lower()
                    contents = ''
                elif tag.name == 'p':
                    contents += '<p>' + tag.text + '</p>'

            # Don't forget the last heading, it's not caught by our loop up above
            if current_heading == 'conservation measures proposed':
                bird.conservation_proposed = contents

            # Increment counter
            counter += 1

    # Research priorities
    counter = 0
    for div in divs:
        ps = div.select('p')
        hs = div.select('h3')
        if len(hs) > 0:
            bird = birds[counter]
            content = ''
            for p in ps:
                content += '<p>' + p.text + '</p>'
            bird.research_priorities = content
            counter += 1

    # Images
    '''
    counter = 0
    imgs = soup.find_all('img')
    img_files_url = os.path.join(settings.BASE_DIR, 'website', 'static', 'distribution_maps')
    for img in imgs:
        if 'finalX' in img['src']:
            bird = birds[counter]
            img_name = img['src'].rsplit('/', 1)[-1]
            old_img_url = os.path.join(img_files_url, img_name)
            new_img_url = os.path.join(img_files_url, bird.scientific_name.lower().replace(' ', '_') + '.png')
            os.rename(old_img_url, new_img_url)
            counter += 1'''

    # Assessor and reviewers
    counter = 0
    redcredits = soup.find_all('div', class_='redcredits')
    for div in redcredits:
        bird = birds[counter]
        ps = div.select('p')
        for p in ps:
            if 'Assessor' in p.text:
                t = p.text.replace('Assessors: ', '')
                t = t.replace('Assessor: ', '')
                bird.assessors = t
            if 'Reviewer' in p.text:
                t = p.text.replace('Reviewers: ', '')
                t = t.replace('Reviewer: ', '')
                bird.reviewers = t
        counter += 1

    for bird in birds:
        try:
            bird.save()
        except:
            import pdb; pdb.set_trace()

    import pdb
    pdb.set_trace()
    return render(request, 'website/index.html', {})

