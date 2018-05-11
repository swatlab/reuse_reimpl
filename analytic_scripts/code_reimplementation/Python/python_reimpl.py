import os, sys, subprocess, csv
import reverse_import, reverse_impl


def shellCommand(command_str):
    cmd = subprocess.Popen(command_str, shell=True, stdout=subprocess.PIPE)
    cmd_out, cmd_err = cmd.communicate()
    return cmd_out


def relativeDistance(removed_invocations, added_invocations, diff_list):
    ref_candidates = list()
    for del_call in removed_invocations:
        for add_call in added_invocations:
            if (add_call[1] - del_call[2] <= 6) and (add_call[1] > del_call[2]):
                if del_call[1] == del_call[0]:
                    ref_candidates.append('(%d, %d) %s -> %s' %(del_call[2], add_call[1], del_call[0], add_call[0]))
                else:
                    ref_candidates.append('(%d, %d) %s[%s] -> %s' %(del_call[2], add_call[1], del_call[1], del_call[0], add_call[0]))
    return ref_candidates

def searchRefactoring(diff_str):    
    ref_candidates = list()
    diff_list = diff_str.split('\n')   
#    print diff_list[4]     # commit message
    # Detect removed entire functions
    removed_import_list = reverse_import.removedImport(diff_list, pip_packages)
    if len(removed_import_list):
#        print '  Removed functions:', removed_import_list
        removed_invocations = reverse_import.removedInvocations(diff_list, removed_import_list)
        if len(removed_invocations):
            added_func_dict = reverse_impl.addedFunctions(diff_list)
            if len(added_func_dict):
                added_invocations = reverse_impl.addedInvocations(diff_list, added_func_dict)
                if DEBUG:
                    print '  Removed func calls:', removed_invocations
                    print '  Added func calls:', added_invocations
                # calculate relative distances
                ref_candidates = relativeDistance(removed_invocations, added_invocations, diff_list)
    return ref_candidates


if __name__ == '__main__':
    DEBUG = False
    # create output directories, if neccessary
    shellCommand('mkdir -p reverse_candidates')
    shellCommand('mkdir -p reverse_patches')
    # perform detections
    if DEBUG:
        pip_packages = ['colander', 'mock', 'six']
    else:
        pip_packages = reverse_import.loadAllPipPackages()
    print 'Detecting code reuse ...'
    
    app_list = os.listdir('py_apps')
    current_dir = os.getcwd()
    
    for an_app in app_list[:]:
        print an_app
        with open('%s/reverse_candidates/%s_candidates.txt' %(current_dir,an_app), 'w') as wf:
            os.chdir('py_apps/%s' %an_app)
            commit_logs = subprocess.check_output('git log --pretty=format:%h'.split())
            for commit_id in commit_logs.split('\n'):
                if len(commit_id):
    #            if len(commit_id) and commit_id == 'c0d08be':
                    if DEBUG:
                        print commit_id
                    diff_str = shellCommand('git show -M99 %s' %commit_id)                    
                    ref_candidates = searchRefactoring(diff_str)
                    if len(ref_candidates):
                        # write results into a file
                        wf.write('%s\n' %commit_id)
                        print ' ', commit_id
                        for can in ref_candidates:
                            print '  ', can
                            wf.write('  %s\n' %can)  
                        wf.write('-' * 50 + '\n')
                        # write the corresponding patches into files
                        shellCommand('mkdir -p %s/reverse_patches/%s' %(current_dir,an_app))
                        with open('%s/reverse_patches/%s/%s.txt' %(current_dir,an_app,commit_id), 'w') as pf:
                            pf.write(diff_str)
        # clean memory
        shellCommand('sudo sysctl -w vm.drop_caches=3')
        # change back to the script's directory
        os.chdir(current_dir)