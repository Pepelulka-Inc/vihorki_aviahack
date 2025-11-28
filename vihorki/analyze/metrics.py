from download_data import downloads

visits, hits, joins = downloads()
print(visits, hits, joins, sep="\n")