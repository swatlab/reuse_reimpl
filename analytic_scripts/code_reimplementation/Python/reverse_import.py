import re, urllib2
from xml.etree import ElementTree

DEBUG = False

# load all available pip packages from pip's website
def loadAllPipPackages():
    print 'Loading pip packages ...'
    url_item = None
    try:
        url_item = urllib2.urlopen('https://pypi.python.org/simple/')
    except:
        print 'Wrong PyPI URL!'
    if url_item:
        page_bytes = url_item.read()
        page_txt = page_bytes.decode('utf-8', 'ignore')
        ascii_str = page_txt.encode('ascii','ignore')
        tree = ElementTree.fromstring(ascii_str)
        url_item.close()
    return [a.attrib['href'] for a in tree.iter('a')]

# decide whether a package is from pip and its used name
def refineImported(package_name, as_names, line, imported_funcs, pip_packages):
    if package_name in pip_packages:
        if type(as_names) == type(''):
            imported_funcs.add((as_names, package_name))
        else:
            for a_n in as_names:
                imported_funcs.add((a_n, package_name))
    return

# identify imported packages from pip
def removedImport(diff_list, pip_packages):
    imported_funcs = set()
    is_py_file = False
    for line in diff_list:
        if line.startswith('--- '):
            if line.endswith('.py') and not(re.search(r'\btest\b', line, re.I)):
                is_py_file = True
            else:
                is_py_file = False
        elif line.startswith('-') and is_py_file:
            purified_line = line[1:].split('#')[0].strip()
            purified_line = re.sub(r'(\\|\(|\))', '', purified_line)
            if purified_line.startswith('import '):  # import pandas as pd
                if re.search(r'import .+? as ', purified_line):
                    matched_import = re.findall(r'import (.+?) as (.+)$', purified_line)                    
                    if len(matched_import):
                        package_name = matched_import[0][0].strip()
                        as_names = matched_import[0][1].strip()
                        refineImported(package_name, as_names, line, imported_funcs, pip_packages)
                else:   # import re, sys
                    matched_import = re.findall(r'import (.+?)$', purified_line)
                    if len(matched_import):
                        for package_name in re.sub(r'\s', '', matched_import[0]).split(','):
                            refineImported(package_name, package_name, line, imported_funcs, pip_packages)
            elif purified_line.startswith('from'):
                if re.search(r'from .+? import\s*\(', purified_line):
                    print line
                if re.search(r'from .+? import .+? as ', purified_line):    # e.g., from collections import Counter as ct
                    matched_import = re.findall(r'from (.+?) import .+ as (.+)', purified_line)
                    if len(matched_import):
                        package_name = matched_import[0][0].strip()
                        as_names = matched_import[0][1].strip()
                        refineImported(package_name, as_names, line, imported_funcs, pip_packages)
                elif re.search(r'from .+? import ', purified_line):     # e.g., from collections import Counter, OrderedDict
                    matched_import = re.findall(r'from (.+?) import (.+)$', purified_line)
                    if len(matched_import):
                        package_name = matched_import[0][0].strip()
                        as_names = re.sub(r'\s', '', matched_import[0][1]).split(',')
                        refineImported(package_name, as_names, line, imported_funcs, pip_packages)
    return imported_funcs
    
# identify the lines where the imported packages are called
def removedInvocations(diff_list, imported_funcs):
    removed_invocations = list()
    self_implemented_funcs = set()
    is_py_file = False
    line_num = 1
    for line in diff_list:
        if line.startswith('--- '):
            if line.endswith('.py'):
                is_py_file = True
                self_implemented_funcs.add(line[4:])
            else:
                is_py_file = False
        elif line.startswith('-') and is_py_file: 
            for im_func in imported_funcs:
                try:
                    if re.search(r'%s(\.\w+?){0,4}\s*\(' %im_func[0], line):
                        if DEBUG:
                            print line_num, line
                        for si in self_implemented_funcs:
                            if not (('/%s/' %im_func[1] in si) or ('/%s.' %im_func[1] in si)):
                                removed_invocations.append([im_func[0], im_func[1], line_num]) # as_name, name, line_num
                                break
                except:
                    print 'Exception of import cases ...'
                    print line
        line_num += 1
    return removed_invocations
    

if __name__ == '__main__':
    pip_packages = loadAllPipPackages()
    
    diff_list = list()
    with open('patch_example3.txt') as f:
        reader = f.read().split('\n')
        for line in reader:
            diff_list.append(line)
    
    
    print removedImport(diff_list, pip_packages)