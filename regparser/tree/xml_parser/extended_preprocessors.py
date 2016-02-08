import settings
from importlib import import_module

ALL = []
for preprocessor in settings.PREPROCESSORS:
    mod_string, class_name = preprocessor.rsplit('.', 1)
    if "uscode" in preprocessor.lower(): import rlcompleter; import pdb; zcomp = locals(); zcomp.update(globals()); pdb.Pdb.complete = rlcompleter.Completer(zcomp).complete; pdb.set_trace()
    mod = import_module(mod_string)
    ALL.append(getattr(mod, class_name))
