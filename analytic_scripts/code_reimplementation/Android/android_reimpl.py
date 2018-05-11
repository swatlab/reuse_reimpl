import sys, subprocess, os, re
from collections import OrderedDict
import pandas as pd

def shellCommand(command_str):
    cmd = subprocess.Popen(command_str, shell=True, stdout=subprocess.PIPE)
    cmd_out, cmd_err = cmd.communicate()
    return cmd_out

def removeBracketsInQuotes(line):
    line = re.sub(r'\\\"', '', line)
    return re.sub(r'\".*?\"', '', line)
    
def addedMethods(diff_list):
    added_method_list = list()
    in_block = False
    brackets = 0
    method_name, param_cnt = None, None
    for line in diff_list:
        cleaned_line = removeBracketsInQuotes(line)
        if cleaned_line.startswith('+') and re.search(method_pattern, cleaned_line):
            method_sig = re.findall('(?:(?:public|private|protected|static|final|native|synchronized|abstract|transient)+\\s)+(?:[\\$_\\w\\<\\>\\[\\]]*)\\s+([\\$_\\w]+)\\(([^\\)]*)\\)?\\s*\\{?[^\\}]*\\}?', cleaned_line)
            method_name = method_sig[0][0]
            if len(method_sig[0][1].strip()) == 0:
                param_cnt = 0
            else:
                param_cnt = method_sig[0][1].count(',') + 1
            in_block = True
            if '{' in cleaned_line:
                brackets += 1
                if '}' in cleaned_line:
                    brackets -= 1
                if brackets == 0:
                    if DEBUG:
                        print 'ENTIRE METHOD FOUND: %s %s\n\n' %(method_name, param_cnt)
                    added_method_list.append([method_name, param_cnt])
                    in_block = False
                    brackets = 0
        elif in_block and cleaned_line.startswith('+'):
            if '{' in cleaned_line:
                brackets += 1
            if '}' in cleaned_line:
                brackets -= 1
            if brackets == 0:
                if DEBUG:
                    print 'ENTIRE METHOD FOUND: %s %s\n\n' %(method_name, param_cnt)
                added_method_list.append([method_name, param_cnt])
                in_block = False
                brackets = 0
        elif in_block == True:
            in_block = False
            brackets = 0
    return added_method_list


def removedInvocations(diff_list):
    imported_classes = dict()
    instance_dict = dict()
    removed_invoc_dict = OrderedDict()
    i = 1
    for line in diff_list:
        if not re.search(r'^(\+|\-)?\s*$', line):
            if line.startswith('-'):
                # collect removed library methods
                matched = re.findall(r'import\s+[\w\.]+\.(\w+)\s*\;', line)
                if matched:
                    full_import_class = line[1:-1]
                    class_name = matched[0]
                    imported_classes[class_name] = full_import_class
                else:
                    # instance of the removed library method
                    instantiated = re.findall(r'(\w+)\s*\[?\s*\w*\s*\]?\s*\=\s*new\s+(\w+)\s*\<?\s*\w*\s*\>?\s*\(.*\)\s*\;', line)
                    if len(instantiated):
                        if instantiated[0][1] in imported_classes:
                            instance_dict[instantiated[0][0]] = imported_classes[instantiated[0][1]]
                    else:
                        # remove redundant white space
                        cleaned_line = re.sub(r'\s+', ' ', line)
                        # whether an instance of a removed library method's invocation is also removed (instance method)
                        for inst in instance_dict:
                            # IS IT ALSO POSSIBLY TO GET AN ATTRIBUTE?
                            invoc = re.findall(r'(\w+)\s*\[?\s*\w*\s*\]?\.\w+\s*\(.*\)\s*\;', cleaned_line)
                            if len(invoc):
                                if invoc[0] == inst:
                                    removed_invoc_dict[i] = instance_dict[inst]
                                    break
                        # whether a removed library method's invocation is also removed (class method)
                        for c in imported_classes:
                            if not ('implements %s' %c in cleaned_line or 'extends %s' %c in cleaned_line):
                                # IS IT ALSO POSSIBLY TO GET AN ATTRIBUTE?    
                                invoc = re.findall(r'(\w+)\.\w+\s*\(.*\)\s*\;', cleaned_line)
                                if len(invoc):
                                    if invoc[0] == c:
                                        removed_invoc_dict[i] = imported_classes[c]
                                        break
        i += 1
    if DEBUG:
        print removed_invoc_dict
    return removed_invoc_dict


def addNearDelPosition(last_removed, removed_cnt, i, line):
    if last_removed:
        position_delta = i - last_removed - removed_cnt
        if DEBUG:
            print 'Pos delta:', position_delta, line
        if position_delta < 5 and position_delta > -5:
            return True
    return False


def addedInvocations(diff_list, added_method_list, removed_invoc_list):
    refact_pairs = set()
    last_removed = None
    removed_cnt = 0
    i = 1
    for line in diff_list:
        if not re.search(r'^(\+|\-)?\s*$', line):
            if line.startswith('+'):
                for m in added_method_list:
                    method_name = m[0]
                    param_cnt = m[1]
                    if (re.search(method_pattern, line)) == None and (method_name in line):
                        matched = re.search(r'\((.+)\)', line)
                        if matched:
                            if len(matched.group(1).strip()) == 0:
                                argument_cnt = 0
                            else:
                                argument_cnt = matched.group(1).count(',')+1
                            if param_cnt == argument_cnt:
                                addedNearby = addNearDelPosition(last_removed, removed_cnt, i, line)
                                if addedNearby:
                                    if DEBUG:
                                        print last_removed, i, line
                                    refact_pairs.add((last_removed, i, last_library))
            elif line.startswith('-'):
                if i in removed_invoc_list:
                    last_removed = i
                    removed_cnt = 0
                    last_library = removed_invoc_list[i]
                elif removed_cnt != None:
                    removed_cnt += 1
        i += 1
    if DEBUG:
        print sorted(refact_pairs)
    return sorted(refact_pairs)


# combine main funcitons to search refactoring from a client method implementation to an API call
def searchRefactoring(diff_str):
    diff_list = diff_str.split('\n')
    # Detect entire added methods        
    added_method_list = addedMethods(diff_list)
    # check whether a library method is removed near a deleted method call
    removed_invoc_list = removedInvocations(diff_list)
    # Check whether an added method's invocation is also added
    refact_res = addedInvocations(diff_list, added_method_list, removed_invoc_list)
    return refact_res

def formatOutput(refact_res):
    formatted_list = list()
    for pair in refact_res:
        formatted_list.append('%s^%s' %(pair[0],pair[1]))
    return '-'.join(formatted_list)

if __name__ == '__main__':
    DEBUG = False
    
    method_pattern = '((public|private|protected|static|final|native|synchronized|abstract|transient)+\\s)+[\\$_\\w\\<\\>\\[\\]]*\\s+[\\$_\\w]+\\([^\\)]*\\)?\\s*\\{?[^\\}]*\\}?'
    current_dir = os.getcwd()
    shellCommand('mkdir -p %s/converse_candidates' %current_dir)
    
    i = 1
    app_names = os.listdir('fdroid_apps')
    for an_app in app_names:
        print 'Analyzing %s (%d) ...' %(an_app,i)
        output_list = list()
        # change to the subject system's directory
        os.chdir('%s/fdroid_apps/%s' %(current_dir,an_app))
        # output commit list
        commit_logs = subprocess.check_output('git log --pretty=format:%h'.split())
        for commit_id in commit_logs.split('\n'):
            if len(commit_id):
                diff_str = shellCommand('git show %s' %commit_id)
                # our current computational resources cannot allow to analyze super huge patches
    	        if sys.getsizeof(diff_str) > 1000000:
                    print '  %s is too big!' %commit_id
                    print '  ' + '-' * 50
                else:            
                    refact_res = searchRefactoring(diff_str)
                    if len(refact_res):
                        # output locations
                        print ' ', commit_id
                        output_list.append(commit_id)
                        for res in refact_res:
                            print '   ', res[0], res[1], '\t', res[2]
                            output_list.append('  (%s, %s)\t%s' %(res[0],res[1],res[2]))
                        print '  ' + '-' * 50
                        output_list.append('-' * 50)
                        # output the patch
                        shellCommand('mkdir -p %s/converse_patches/%s' %(current_dir,an_app))
                        with open('%s/converse_patches/%s/%s.txt' %(current_dir,an_app,commit_id), 'w') as pf:
                            pf.write(diff_str)
        if len(output_list):
            with open('%s/converse_candidates/%s_candidates.txt' %(current_dir,an_app), 'w') as wf:
                wf.write('\n'.join(output_list))
        i += 1
                        

