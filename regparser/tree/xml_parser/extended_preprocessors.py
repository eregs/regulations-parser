import settings
from importlib import import_module

ALL = []
for preprocessor in settings.PREPROCESSORS:
    mod_string, class_name = preprocessor.rsplit('.', 1)
    mod = import_module(mod_string)
    ALL.append(getattr(mod, class_name))
