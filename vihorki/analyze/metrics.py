from download_data import downloads
import pandas as pd

def get_metrics():
    hits = pd.read_hdf("data/hits.h5", 'key')
    visits = pd.read_hdf("data/visits_f.h5", 'key')
    joins = pd.read_hdf('data/joins_f.h5', 'key')
    return visits, hits, joins
