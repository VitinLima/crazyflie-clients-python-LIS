import json
import os
from appdirs import AppDirs
import sys

from .Backend import Backend

# Path used all over the application
if not hasattr(sys, 'frozen'):
    module_path = os.path.dirname(__file__)
else:
    module_path = os.path.join(os.path.dirname(sys.executable),
                               'lib', 'lis')
config_path = AppDirs("cfclient", "Bitcraze").user_config_dir

__author__ = 'Interns from the Laboratoir d\'Ingénierie de Systèmes de l\'École Nationale Supérieure de Caen'
__all__ = []

lis_backend = Backend()