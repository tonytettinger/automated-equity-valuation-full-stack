import os


def get_links_from_static():
    static = os.listdir('static')
    links = []
    for file in static:
        if file.startswith('index'):
            continue
        if file.endswith('.html'):
            file_without_extension = file[:-5]
            links.append((file, file_without_extension))
    return links