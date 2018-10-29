import pstats
p = pstats.Stats('data.pyprof')
p.sort_stats('cumulative').print_stats()
