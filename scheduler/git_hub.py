import os
from datetime import datetime

import sh

current_directory = os.path.dirname(os.path.abspath(__file__))
# https://stackoverflow.com/questions/1456269/python-git-module-experiences
def add_all_and_commit():

    git = sh.git.bake(_cwd=current_directory)
    time_string = datetime.today().strftime('%Y-%m-%d')

    print(git.status())
    print(current_directory)
    print(git.add('.'))
    #print(git.commit(m=f'{time_string} commit message'))
    #print(git.push())
    print(git.status())

add_all_and_commit()