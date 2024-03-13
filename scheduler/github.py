import os
from datetime import datetime

import sh

current_directory = os.path.dirname(os.path.abspath(__file__))
# https://stackoverflow.com/questions/1456269/python-git-module-experiences
def add_all_in_static_and_commit():
    print('starting to commit files')
    git = sh.git.bake(_cwd=current_directory)
    print('current working dir', current_directory)
    time_string = datetime.today().strftime('%Y-%m-%d')

    print(git.pull())
    print(git.status())
    print(current_directory)
    print(git.add('../static/'))
    print(git.commit(m=f'{time_string} new html files have been generated after running scheduled checks'))
    print(git.push())
    print(git.status())
    print('Successfully committed files to GitHub')
