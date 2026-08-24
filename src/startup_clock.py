"""Horloge capturée avant le chargement des dépendances applicatives lourdes."""

import time


PROCESS_STARTED_NS = time.monotonic_ns()
