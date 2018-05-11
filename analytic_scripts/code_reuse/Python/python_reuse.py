import os, sys, subprocess
import added_func, removed_func

def shellCommand(command_str):
    cmd = subprocess.Popen(command_str, shell=True, stdout=subprocess.PIPE)
    cmd_out, cmd_err = cmd.communicate()
    return cmd_out

def findBlock(line_num, consecutive_blocks):
    '''for bloc in consecutive_blocks:
        if line_num in bloc:
            return bloc[0], bloc[-1], bloc.index(line_num)+1'''
    sec_idx = 0
    for line_sec in consecutive_blocks:
        last_elem = None
        context_cnt = 0
        for bloc in line_sec:
            if last_elem:
                context_cnt += (bloc[0] - last_elem - 1)
            
            if line_num in bloc:
                #return bloc[0], bloc[-1], bloc.index(line_num)+1
                return sec_idx, bloc.index(line_num), context_cnt
                
            else:
                last_elem = bloc[-1]
        sec_idx += 1
    return

def relativeDistance(removed_invocations, added_invocations, diff_list):
    ref_candidates = list()
    consecutive_blocks = list()
    line_num = 1
    line_type = None
    
    for line in diff_list:
        if DEBUG:
            print line_num, line
        if line.startswith('@@ '):
            line_section = list()
            consecutive_blocks.append(line_section)
        else:  
            if line.startswith('-') and (not line.startswith('---')):                
                if line_type == 'removed':
    #                consecutive_blocks[-1].append(line_num)
                    line_section[-1].append(line_num)
                else:
                    line_type = 'removed'
                    current_block = [line_num]
    #                consecutive_blocks.append(current_block)
                    line_section.append(current_block)
            elif line.startswith('+') and (not line.startswith('+++')):
                if line_type == 'added':
    #                consecutive_blocks[-1].append(line_num)
                    line_section[-1].append(line_num)
                else:
                    line_type = 'added'
                    current_block = [line_num]
    #                consecutive_blocks.append(current_block)
                    line_section.append(current_block)
            else:
                line_type = None        
        line_num += 1

#    print consecutive_blocks
    
    
    for del_call in removed_invocations:
            del_sec, del_pos, del_context = findBlock(del_call[1], consecutive_blocks)
            for add_call in added_invocations:
                add_sec, add_pos, add_context = findBlock(add_call[2], consecutive_blocks)
                if add_sec == del_sec and (add_pos - del_pos + (add_context - del_context)) < 5:
                #if abs(add_pos - del_pos + (add_start - del_end)) < 5:# or abs(add_pos - del_pos + (del_start - add_end)) < 5:
    #                print add_start, del_end
                    if add_call[1] == add_call[0]:
    #                    print '  (%d, %d) %s -> %s' %(del_call[1], add_call[2], del_call[0], add_call[0])
                        ref_candidates.append('(%d, %d) %s -> %s' %(del_call[1], add_call[2], del_call[0], add_call[0]))
                    else:
    #                    print '  (%d, %d) %s -> %s[%s]' %(del_call[1], add_call[2], del_call[0], add_call[1], add_call[0])
                        ref_candidates.append('(%d, %d) %s -> %s[%s]' %(del_call[1], add_call[2], del_call[0], add_call[1], add_call[0]))

    '''for del_call in removed_invocations:
        del_start, del_end, del_pos = findBlock(del_call[1], consecutive_blocks)
        for add_call in added_invocations:
            add_start, add_end, add_pos = findBlock(add_call[2], consecutive_blocks)
            if abs(add_pos - del_pos + (add_start - del_end)) < 5:# or abs(add_pos - del_pos + (del_start - add_end)) < 5:
                print add_start, del_end
                if add_call[1] == add_call[0]:
#                    print '  (%d, %d) %s -> %s' %(del_call[1], add_call[2], del_call[0], add_call[0])
                    ref_candidates.append('(%d, %d) %s -> %s' %(del_call[1], add_call[2], del_call[0], add_call[0]))
                else:
#                    print '  (%d, %d) %s -> %s[%s]' %(del_call[1], add_call[2], del_call[0], add_call[1], add_call[0])
                    ref_candidates.append('(%d, %d) %s -> %s[%s]' %(del_call[1], add_call[2], del_call[0], add_call[1], add_call[0]))
    return ref_candidates'''
    return ref_candidates

def searchRefactoring(diff_str):    
    ref_candidates = list()
    diff_list = diff_str.split('\n')   
#    print diff_list[4]     # commit message
    # Detect removed entire functions
    removed_func_list = removed_func.removedFunctions(diff_list)
    if len(removed_func_list):
#        print '  Removed functions:', removed_func_list
        removed_invocations = removed_func.removedInvocations(diff_list, removed_func_list)
        if len(removed_invocations):
            imported_funcs = added_func.importedModules(diff_list, pip_packages)
#            print '  Imported packages:', imported_funcs
            if len(imported_funcs):
                added_invocations = added_func.importedInvocations(diff_list, imported_funcs)
                if DEBUG:
                    print '  Removed func calls:', removed_invocations
                    print '  Imported func calls:', added_invocations
                # calculate relative distances
                ref_candidates = relativeDistance(removed_invocations, added_invocations, diff_list)
                if DEBUG:
                    print '-'*30
    return ref_candidates

if __name__ == '__main__':
    DEBUG = False
    # create output directories, if neccessary
    shellCommand('mkdir -p py_candidates')
    shellCommand('mkdir -p py_patches')
    # perform detections
    pip_packages = added_func.loadAllPipPackages()
#    pip_packages = ['colander', 'mock', 'six']
    print 'Detecting code reuse ...'
    # WE SHOULD MAKE A LOOP HERE
    current_dir = os.getcwd()
    an_app = 'kinto'
    
    with open('%s/py_candidates/%s_candidates.txt' %(current_dir,an_app), 'w') as wf:
        os.chdir('py_apps/%s' %an_app)
        commit_logs = subprocess.check_output('git log --pretty=format:%h'.split())
        for commit_id in commit_logs.split('\n'):
            if len(commit_id):
#            if len(commit_id) and commit_id == '5df0c15':
                print commit_id
                diff_str = shellCommand('git show -M99 %s' %commit_id)
    #            if sys.getsizeof(diff_str) > 1000000:
                ref_candidates = searchRefactoring(diff_str)
                if len(ref_candidates):
                    # write results into a file
                    wf.write('%s\n' %commit_id)
                    for can in ref_candidates:
                        print '  ', can
                        wf.write('  %s\n' %can)  
                    wf.write('-' * 50 + '\n')
                    # write the corresponding patches into files
                    shellCommand('mkdir -p %s/py_patches/%s' %(current_dir,an_app))
                    with open('%s/py_patches/%s/%s.txt' %(current_dir,an_app,commit_id), 'w') as pf:
                        pf.write(diff_str)
