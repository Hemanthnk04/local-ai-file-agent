
import os
from .config import IGNORE_DIRS,IGNORE_EXT

def scan_folder(path):

    if not path:
        path=os.getcwd()

    files=[]

    for root,dirs,fs in os.walk(path):

        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for f in fs:

            if any(f.endswith(e) for e in IGNORE_EXT):
                continue

            files.append(os.path.join(root,f))

    return files
