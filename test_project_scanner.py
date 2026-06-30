from pathlib import Path
from pprint import pprint
from services.project_scanner import scan_project

metadata = scan_project(".")
pprint(metadata)