import os


def get_links_from_static():
    links = []

    static_dir = os.path.abspath(os.path.join(__file__, '../../static'))

    for file in os.listdir(static_dir):
        if file.startswith('index'):
            continue
        if file.endswith('.html'):
            file_without_extension = file[:-5]
            links.append((file, file_without_extension))
    return links
