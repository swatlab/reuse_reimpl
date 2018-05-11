import re

DEBUG = False

# literally parse arguments, remove quotes and comments
def parseArgs(line):
    end_definition = False
    cleaned_argu = list()    
    in_quotes = None
    for l in line:
        # skip characters in quotes
        if in_quotes:
            if l == in_quotes:
                in_quotes = None            
        else:
             if l == '"' or l == "'":
                 in_quotes = l
             elif l == ')':
                 end_definition = True
                 break
             else:
                cleaned_argu.append(l)
    quote_free_str = ''.join(cleaned_argu)
    return re.sub(r'\#.*$', '', quote_free_str), end_definition

def simpleCountArgs(arg_string):
    arg_list = arg_string.strip().split(',')
    if arg_list == []:
        arg_cnt = 0
    elif arg_list[0].strip() == 'cls' or arg_list[0].strip() == 'self':
            arg_cnt = len(arg_list) -1
    else:
        arg_cnt = len(arg_list)
    return arg_cnt

# calculate the number of arguments
def countArgs(arg_string, matched_def, complete_def):
    arg_cnt = simpleCountArgs(arg_string)
    matched_def = False
    complete_def = True
    return arg_cnt, matched_def, complete_def

# calculate the indent level of a line
def calculateIndent(line):
    if len(line.strip()) == 0:  # if a line is blank, we consider it as with a huge indent
        return 999999
    return len(line.split(line.lstrip())[0].expandtabs(4))

# reset intermediate variable for the remove function detection
def resetRemoveVariables(complete_def, in_removed, indent, func_name):
    complete_def = False
    in_removed = False
    indent = None
    func_name = ''
    if DEBUG:
        print '-'*30
    return complete_def, in_removed, indent, func_name

def entirelyRemoved(complete_def, in_removed, indent, func_name, arg_cnt, removed_func_dict):
    if DEBUG:
        print '\t(Entirely removed function: %s %d)' %(func_name,arg_cnt)
    #########removed_func_dict.add((func_name,arg_cnt))    
    
    if func_name in removed_func_dict:
        removed_func_dict[func_name].add(arg_cnt)
    else:
        removed_func_dict[func_name] = set([arg_cnt])
    
    return resetRemoveVariables(complete_def, in_removed, indent, func_name)

def partiallyRemoved(complete_def, in_removed, indent, func_name):
    if DEBUG:
        print '\t(Partially removed function)'
    return resetRemoveVariables(complete_def, in_removed, indent, func_name)

# detect entirely removed functions / methods
def removedFunctions(diff_list):
    # result list
    removed_func_dict = dict()
    # intermediate variables
    is_py_file = False
    matched_def = False
    unparsed_line = ''
    arg_string = ''
    func_name = ''
    indent = None
    complete_def = False
    in_removed = False
    last_cnt = len(diff_list) - 1
    # heuristic
    for line in diff_list:
        if line.startswith('--- '):
            if line.endswith('.py') and not(re.search(r'\btest\b', line, re.I)):
                is_py_file = True
            else:
                is_py_file = False
        elif is_py_file:
            #line = line.decode('utf-8')
            line = unicode(line, errors='replace')
            if complete_def and (line.strip().startswith('#') or line[1:].strip().startswith('#')):    # skip comment lines
                if DEBUG:
                    print line
            elif line.startswith('-'):    
                # remove the "-" at the beginning
                purified_line = line[1:]
                # identify a function name, and parse the rest of the funciton definition                    
                if matched_def:
                    analyzed_line = unparsed_line + purified_line
                    unparsed_line = ''
                else:
                    match_res = re.findall(r'^\s*?def\s+?(\w+?)\s*\((.+)', purified_line)
                    if match_res:
                        # in case where the above lines are white spaces
                        if complete_def:
                            if DEBUG:
                                print line
                            complete_def, in_removed, indent, func_name = entirelyRemoved(complete_def, in_removed, indent, func_name, arg_cnt, removed_func_dict)
                        # analyze a new removed definition
                        analyzed_line = match_res[0][1]
                        func_name = match_res[0][0]
                        if func_name != '__init__':
                            matched_def = True
                            indent = calculateIndent(purified_line)
                # literally parse a line
                if matched_def:
                    if DEBUG:
                        print line
                    if analyzed_line.endswith('\\'):
                        unparsed_line = analyzed_line[:-1]
                    else:
                        unparsed_line = ''
                        cleaned_str, end_definition = parseArgs(analyzed_line)
                        arg_string += cleaned_str
                        if end_definition:
                            arg_cnt, matched_def, complete_def = countArgs(arg_string, matched_def, complete_def)
                            arg_string = ''
                elif complete_def:
                    if DEBUG:
                        print line
                    if in_removed and calculateIndent(line[1:]) <= indent:
                        complete_def, in_removed, indent, func_name = entirelyRemoved(complete_def, in_removed, indent, func_name, arg_cnt, removed_func_dict)
                    in_removed = True
                    # if this is the last elem in the list
                    if last_cnt == 0:
                        complete_def, in_removed, indent, func_name = entirelyRemoved(complete_def, in_removed, indent, func_name, arg_cnt, removed_func_dict)
            else:
                matched_def = False
                if complete_def and in_removed:   # in case where a function's definition and its another line are removed
                    if DEBUG:
                        print line
                    if line.startswith('+'):
                        if calculateIndent(line[1:]) <= indent:     # if an added line is with less indent, entirely removed
                            complete_def, in_removed, indent, func_name = entirelyRemoved(complete_def, in_removed, indent, func_name, arg_cnt, removed_func_dict)
                        elif calculateIndent(line[1:]) > indent:    # if an added line is with less indent, partially removed
                            complete_def, in_removed, indent, func_name = partiallyRemoved(complete_def, in_removed, indent, func_name)
                    elif line.startswith(' '):
                        if len(line[1:].strip()):
                            if calculateIndent(line[1:]) <= indent: # if a context line is with less indent, entirely removed
                                complete_def, in_removed, indent, func_name = entirelyRemoved(complete_def, in_removed, indent, func_name, arg_cnt, removed_func_dict)
                    elif line.startswith('@@'):                     # when meet a separator line, entirely removed
                        complete_def, in_removed, indent, func_name = entirelyRemoved(complete_def, in_removed, indent, func_name, arg_cnt, removed_func_dict)    
                elif complete_def:    # in case where only a funtion's definition is removed but the next line doesn't start with "-", partially removed
                    if DEBUG:
                        print line
                    complete_def = False
                    complete_def, in_removed, indent, func_name = partiallyRemoved(complete_def, in_removed, indent, func_name)
        # count the distance to the last elem in the diff list
        last_cnt -= 1
    return removed_func_dict

def parseArgsOfInvocation(arg_string, matched_name, analyzed_line, func_name, line_num, removed_func_dict, removed_invocations):
    cleaned_str, end_definition = parseArgs(analyzed_line)
    arg_string += cleaned_str
    if end_definition:
        if DEBUG:
            print arg_string, simpleCountArgs(arg_string)
        ########if (func_name, simpleCountArgs(arg_string)) in removed_func_dict:
        if func_name in removed_func_dict:
            if simpleCountArgs(arg_string) in removed_func_dict[func_name]:
                if DEBUG:
                    print 'found', func_name, simpleCountArgs(arg_string)
                removed_invocations.append([func_name, line_num])
        matched_name = False
        arg_string = ''
    return arg_string, matched_name

def removedInvocations(diff_list, removed_func_dict):
    removed_invocations = list()
    is_py_file = False
    matched_name = False
    unparsed_line, arg_string = '', ''
    line_num = 1
    for line in diff_list:
        if line.startswith('--- '):
            if line.endswith('.py'):
                is_py_file = True
            else:
                is_py_file = False
        elif is_py_file:
            #line = line.decode('utf-8')
            line = unicode(line, errors='replace')
            if line.startswith('-') and is_py_file:
                purified_line = line[1:]    # remove the "-" at the beginning
                if not (purified_line.lstrip().startswith('def') or purified_line.lstrip().startswith('class') or purified_line.lstrip().startswith('#')):
                    if matched_name:    # match the rest line(s) of the function call
                        analyzed_line = unparsed_line + purified_line
                        if analyzed_line.endswith('\\'):
                            unparsed_line = analyzed_line[:-1]
                        else:
                            unparsed_line = ''
                            arg_string, matched_name = parseArgsOfInvocation(arg_string, matched_name, analyzed_line, func_name, line_num, removed_func_dict, removed_invocations)
                    else:                   # match the first line of a function call
                        has_parenthese = re.findall('(\w+)\s*?\((.*?)', line)
                        if len(has_parenthese):
                            func_name = has_parenthese[0][0].split('.')[-1]
                            if func_name in removed_func_dict:                            
                                if DEBUG:
                                    print line
                                matched_name = True
                                analyzed_line = re.findall('%s\s*?\((.*?)$' %func_name, line)[0]
                                arg_string, matched_name = parseArgsOfInvocation(arg_string, matched_name, analyzed_line, func_name, line_num, removed_func_dict, removed_invocations)
        line_num += 1
    return removed_invocations 

if __name__ == '__main__':
    diff_list = list()
    with open('b149d38.txt') as f:
        reader = f.read().split('\n')
        for line in reader:
            diff_list.append(line)
    
    removed_func_dict = removedFunctions(diff_list)
    print removed_func_dict
    
    print ''
    print '*'*100
    removed_invocations = removedInvocations(diff_list, removed_func_dict)
    print removed_invocations
    