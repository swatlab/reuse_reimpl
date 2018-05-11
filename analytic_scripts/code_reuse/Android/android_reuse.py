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
    
def removedMethods(diff_list):
    removed_method_list = list()
    in_block = False
    brackets = 0
    method_name, param_cnt = None, None
    for line in diff_list:
        cleaned_line = removeBracketsInQuotes(line)
        if cleaned_line.startswith('-') and re.search(method_pattern, cleaned_line):
            method_sig = re.findall('(?:(?:public|private|protected|static|final|native|synchronized|abstract|transient)+\\s)+(?:[\\$_\\w\\<\\>\\[\\]]*)\\s+([\\$_\\w]+)\\(([^\\)]*)\\)?\\s*\\{?[^\\}]*\\}?', cleaned_line)
            method_name = method_sig[0][0]
            if len(method_sig[0][1].strip()) == 0:
                param_cnt = 0
            else:
                param_cnt = method_sig[0][1].count(',') + 1
            if DEBUG:
                print cleaned_line
            in_block = True
            if '{' in cleaned_line:
                brackets += 1
                if '}' in cleaned_line:
                    brackets -= 1
                if brackets == 0:
                    if DEBUG:
                        print 'ENTIRE METHOD FOUND: %s %s\n\n' %(method_name, param_cnt)
                    removed_method_list.append([method_name, param_cnt])
                    in_block = False
                    brackets = 0
        elif in_block and cleaned_line.startswith('-'):
            if DEBUG:
                print cleaned_line
            if '{' in cleaned_line:
                brackets += 1
            if '}' in cleaned_line:
                brackets -= 1
            if brackets == 0:
                if DEBUG:
                    print 'ENTIRE METHOD FOUND: %s %s\n\n' %(method_name, param_cnt)
                removed_method_list.append([method_name, param_cnt])
                in_block = False
                brackets = 0
        elif in_block == True:
            in_block = False
            brackets = 0
            if DEBUG:
                print '\n'*3
    return removed_method_list

def removedInvocations(diff_list, removed_method_list):
    removed_calls = OrderedDict()
    i = 1
    prior_removed_lines = 0
    for line in diff_list:
        if not re.search(r'^(\+|\-)?\s*$', line):
            if line.startswith('-'):
                for m in removed_method_list:
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
                                if DEBUG:
                                    print i, line, prior_removed_lines
                                removed_calls[i] = prior_removed_lines
                prior_removed_lines += 1
            else:
                prior_removed_lines = 0
        i += 1
    if DEBUG:
        print removed_calls
        print '\n'*5
    return removed_calls

def addNearDelPosition(last_removed, removed_calls, i, line):
    if last_removed:
        position_delta = i - last_removed - removed_calls.get(last_removed)
        if DEBUG:
            print 'Pos delta:', position_delta
        if position_delta < 5 and position_delta > -5:
            # THIS THE THE REMOVE/ADD PAIR THAT NEED TO BE OUTPUTED
            if DEBUG:
                print last_removed, i, line
            return last_removed, i
    return False

def addedInvocations(diff_list, removed_calls, refact_res):
    i = 1
    imported_classes = dict()
    last_removed = None
    new_added_cnt = 0
    instance_dict = dict()
    for line in diff_list:
        if not re.search(r'^(\+|\-)?\s*$', line):
            if line.startswith('+'):
                # collect new imported classes
                matched = re.findall(r'import\s+[\w\.]+\.(\w+)\s*\;', line)
                if matched:
                    full_import_class = line[1:-1]
                    class_name = matched[0]
                    imported_classes[class_name] = full_import_class
                else:
                    # instance of the new imported classes
                    instantiated = re.findall(r'(\w+)\s*\[?\s*\w*\s*\]?\s*\=\s*new\s+(\w+)\s*\<?\s*\w*\s*\>?\s*\(.*\)\s*\;', line)
                    if len(instantiated):
                        if instantiated[0][1] in imported_classes:
                            instance_dict[instantiated[0][0]] = imported_classes[instantiated[0][1]]
                    else:
                        # remove redundant white space
                        cleaned_line = re.sub(r'\s+', ' ', line)
                        # whether an instance of a new imported class is invocated (instance method)
                        for inst in instance_dict:
                            # IS IT ALSO POSSIBLY TO GET AN ATTRIBUTE?
                            invoc = re.findall(r'(\w+)\s*\[?\s*\w*\s*\]?\.\w+\s*\(.*\)\s*\;', cleaned_line)
                            if len(invoc):
                                if invoc[0] == inst:
                                    addedNearby = addNearDelPosition(last_removed, removed_calls, i, line)
                                    if addedNearby:
                                        #print cleaned_line, instance_dict[inst]
                                        refact_res.append([addedNearby, instance_dict[inst]])
                                        break
                        # whether a new imported class is invocated (class method)
                        for c in imported_classes:
                            if not ('implements %s' %c in cleaned_line or 'extends %s' %c in cleaned_line):
                                # IS IT ALSO POSSIBLY TO GET AN ATTRIBUTE?    
                                invoc = re.findall(r'(\w+)\.\w+\s*\(.*\)\s*\;', cleaned_line)
                                if len(invoc):
                                    if invoc[0] == c:
                                        addedNearby = addNearDelPosition(last_removed, removed_calls, i, line)
                                        if addedNearby:
                                            #print cleaned_line, imported_classes[c]
                                            refact_res.append([addedNearby, imported_classes[c]])
                                            break
                new_added_cnt += 1
            else:
                new_added_cnt = 0
                if line.startswith('@@'):
                    last_removed = None
                elif i in removed_calls:
                    if DEBUG:
                        print i, removed_calls[i]
                    last_removed = i
        i += 1
    return

# combine main funcitons to search refactoring from a client method implementation to an API call
def searchRefactoring(diff_str):
    refact_res = list()    
    diff_list = diff_str.split('\n')
    # Detect removed entire methods        
    removed_method_list = removedMethods(diff_list)
    if DEBUG:
        print removed_method_list
    # Check whether a removed method's invocation is also removed
    removed_calls = removedInvocations(diff_list, removed_method_list)
    # check whether a new class is imported, and used near a deleted method call
    addedInvocations(diff_list, removed_calls, refact_res)
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
    shellCommand('mkdir -p %s/app_candidates' %current_dir)
    
    i = 1
    app_names = os.listdir('fdroid_apps')
    for an_app in app_names:
        if os.path.exists('%s/app_candidates/%s_candidates.txt' %(current_dir,an_app)):
            print 'Skipping %s ...' %an_app
        else:
            # change to the subject system's directory
            os.chdir('%s/fdroid_apps/%s' %(current_dir,an_app))
            print 'Analyzing %s (%d) ...' %(an_app,i)
            output_list = list()
            # output commit list
            commit_logs = subprocess.check_output('git log --pretty=format:%h'.split())
            for commit_id in commit_logs.split('\n'):
                if len(commit_id):
                    diff_str = shellCommand('git show %s' %commit_id)
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
                                print '   ', res[0], '\t', res[1]
                                output_list.append('  %s\t%s' %(res[0],res[1]))
                            print '  ' + '-' * 50
                            output_list.append('-' * 50)
                            # output the patch
                            shellCommand('mkdir -p %s/app_patches/%s' %(current_dir,an_app))
                            with open('%s/app_patches/%s/%s.txt' %(current_dir,an_app,commit_id), 'w') as pf:
                                pf.write(diff_str)
            if len(output_list):
                with open('%s/app_candidates/%s_candidates.txt' %(current_dir,an_app), 'w') as wf:
                    wf.write('\n'.join(output_list))
            i += 1
    # change back to the current directory                    
    os.chdir(current_dir)
