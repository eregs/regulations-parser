from contextlib import contextmanager
import os
import shelve

from dagger import dagger

from . import ROOT


class Missing(Exception):
    def __init__(self, key, dependency):
        super(Missing, self).__init__(
            "Missing dependency. {} is needed for {}".format(
                dependency, key))
        self.dependency = dependency
        self.key = key


class Graph(object):
    """Track dependencies between input and output files, storing them in
    `dependencies.db` for later retrieval. This lets us know that an output
    with dependencies needs to be updated if those dependencies have been
    updated"""
    DB_FILE = os.path.join(ROOT, "dependencies.db")

    def __init__(self):
        if not os.path.exists(ROOT):
            os.makedirs(ROOT)
        self.dag = dagger()
        self._ran = False

        with self.dependency_db() as db:
            for key, dependencies in db.items():
                self.dag.add(key, dependencies)

    @contextmanager
    def dependency_db(self):
        """Python 2 doesn't have a context manager for shelve.open, so we've
        created one"""
        db = shelve.open(self.DB_FILE)
        try:
            yield db
        finally:
            db.close()

    def add(self, output_entry, input_entry):
        """Add a dependency where output tuple relies on input_tuple"""
        self._ran = False
        from_str, to_str = str(output_entry), str(input_entry)

        self.dag.add(from_str, [to_str])
        with self.dependency_db() as db:
            deps = db.get(from_str, set())
            deps.add(to_str)
            db[from_str] = deps

    def _run_if_needed(self):
        if not self._ran:
            self.dag.run()
            self._ran = True

    def validate_for(self, entry):
        """Raise an exception if a particular output has stale dependencies"""
        self._run_if_needed()
        key = str(entry)
        with self.dependency_db() as db:
            for dependency in db[key]:
                if self.dag.get(dependency).stale:
                    raise Missing(key, dependency)

    def is_stale(self, entry):
        """Determine if a file needs to be rebuilt"""
        self._run_if_needed()
        return bool(self.dag.get(str(entry)).stale)
