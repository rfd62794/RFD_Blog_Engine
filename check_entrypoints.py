import importlib.metadata
eps = importlib.metadata.entry_points(group='pytest11')
for ep in eps:
    print(ep.name, ep.value)
