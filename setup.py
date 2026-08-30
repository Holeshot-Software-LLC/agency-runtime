"""Register the minimal custom commands required by the reviewed wheel contract."""

import importlib
import os
import sys

from setuptools import setup

_SOURCE_ROOT = os.path.dirname(os.path.abspath(__file__))
if _SOURCE_ROOT not in sys.path:
    sys.path.insert(0, _SOURCE_ROOT)

COMMAND_CLASSES = importlib.import_module("scripts.platform_wheel").COMMAND_CLASSES

setup(cmdclass=COMMAND_CLASSES)
