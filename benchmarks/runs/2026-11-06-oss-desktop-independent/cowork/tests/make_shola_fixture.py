"""A synthetic shola plot survey shaped like a real field file (no real data).

Sheets: grown trees (girth, height), seedlings and saplings per 2x2 m subplot (with header rows repeated mid-sheet,
as field files often have), cestrum density, and a Read me that explains the species codes. Recorders are fake
people; sites are real-sounding Nilgiris places. Usage: make_shola_fixture.py <out.xlsx>
"""
import random
import sys

import openpyxl

SPECIES = {  # code: (name, habit, invasive)
    'cesaur': ('Cestrum aurantiacum', 'Shrub', True), 'ageade': ('Ageratina adenophora', 'Shrub', True),
    'lancam': ('Lantana camara', 'Shrub', True), 'acamea': ('Acacia mearnsii', 'Tree', True),
    'rapcap': ('Rapanea capitellata', 'Tree', False), 'neosco': ('Neolitsea scrobiculata', 'Tree', False),
    'syzcal': ('Syzygium calophyllifolium', 'Tree', False), 'ilewig': ('Ilex wightiana', 'Tree', False),
    'rhoarb': ('Rhododendron arboreum', 'Tree', False), 'mahlax': ('Mahonia leschenaultii', 'Shrub', False),
    'psyele': ('Psychotria elongata', 'Shrub', False), 'litwig': ('Litsea wightiana', 'Tree', False),
    'eurnit': ('Eurya nitida', 'Tree', False), 'gaumyr': ('Gaultheria fragrantissima', 'Shrub', False),
}
SITES = ['Bikkapathimund', 'Avalanche', 'Korakundah']
RECORDERS = ['Meena Raghavan', 'Arjun Bellie', 'Kavya Shenoy', 'Joseph Mathan']


def main(out):
    rnd = random.Random(7)
    book = openpyxl.Workbook()
    trees = book.active
    trees.title = 'Raw 10x10m Data'
    trees.append(['Site', 'Block code', 'Transect', 'Plot', 'sppnam', 'gbh_cm', 'height_m', 'Recorder', 'Date'])
    tree_species = [c for c, (_, habit, _) in SPECIES.items() if habit == 'Tree']
    for site_i, site in enumerate(SITES):
        for transect in range(1, 4):
            for plot in range(1, 6):
                for _ in range(rnd.randint(6, 12)):
                    sp = rnd.choice(tree_species + ['rapcap', 'neosco', 'acamea' if plot == 1 else 'syzcal'])
                    big = 2.4 if sp in ('rapcap', 'syzcal') else 1.4 if sp == 'acamea' else 1
                    gbh = round(rnd.lognormvariate(3.6, .5) * big, 1)
                    trees.append([site, chr(65 + site_i), transect, plot, sp, gbh, round(gbh / 9 + rnd.random() * 4, 1),
                                  rnd.choice(RECORDERS), f'2025-0{site_i + 2}-1{transect}'])
    sap = book.create_sheet('2x2m Seedlings and saplings')
    header = ['hab', 'blo cod', 'tranum', 'plot', 'subplot', 'sppnam', 'numsee', 'numsap', 'grass_pct', 'bare_pct',
              'soil_moisture']
    sap.append(header)
    shrubs = list(SPECIES)
    for transect in range(1, 8):
        if transect == 4:
            sap.append(header)  # a repeated header row, as in field files
        for plot in range(1, 6):
            for subplot in range(1, 5):
                cest = rnd.random() < .85
                for sp in rnd.sample(shrubs, 5) + (['cesaur'] if cest else []):
                    if sp == 'ageade' and transect not in (1, 4, 5):
                        continue
                    habit = SPECIES[sp][1]
                    n = rnd.randint(0, 60 if sp == 'cesaur' else 12)
                    sap.append([habit, 1, transect, plot, subplot, sp, n, rnd.randint(0, n // 2 + 1),
                                rnd.randint(2, 12) if cest else rnd.randint(10, 30), rnd.randint(0, 20),
                                rnd.choice(['', '', '', 'moist', 'dry'])])
    dens = book.create_sheet('Density')
    dens.append(['Transect', 'Plot', 'Cestrum density in each plot'])
    for transect in range(1, 8):
        for plot in range(1, 6):
            dens.append([transect, plot, round(rnd.random() * 9, 2)])
    readme = book.create_sheet('Read me')
    readme.append(['Shola plot survey, Nilgiris. Grown trees in 10x10 m plots; seedlings and saplings in 2x2 m subplots.'])
    readme.append(['Plot 1 is at the shola edge; each next plot is 10 m further in.'])
    readme.append(['Species are 6-letter codes (first 3 letters of genus + species).'])
    readme.append(['cesaur is Cestrum, the invasive shrub we track in the Density sheet.'])
    readme.append(['Contact Meena Raghavan for questions about this file.'])
    book.save(out)


if __name__ == '__main__':
    main(sys.argv[1])
