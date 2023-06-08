#!/usr/bin/env python
"""
This module runs SCAPS in parallel in a series of WINE VMs
"""

from __future__ import unicode_literals, division

__author__ = "Daniil Kitchaev"
__version__ = "1.0"
__maintainer__ = "Daniil Kitchaev"
__email__ = "dkitch@mit.edu"
__status__ = "Development"
__date__ = "July 20, 2016"

import os
import shutil
import subprocess
from multiprocessing import Process, Queue
import time
from copy import deepcopy
import random

class SCAPSrunner:
    ##################################################################################################################
    # Change these defaults as necessary depending on system configuration
    """ this used to say MAX_CORENUM = 32 """
    MAX_CORENUM = 3 # Should be roughly doubly the number of physical cores, and equal to the number of proc folders
                    # in the SCAPS exec folder

        # these set of lines are calling a set of actual files in some filepath
        # the filepath starts with {} which must allow it to reference some generic home?
        # what does .format(ROOTDIR) do?
        # things defined within SCAPSrunner are functions that are called with SCAPSrunner.examplefunction()
        # Specifically, since run_forward_simulation calls SCAPSrunner = scaps_runner, it will be scaps_runner.examplefunction()
        # it accomplishes this by def examplefunction()
        # list of functions =   
        # __init__
            # basic starting function
            # takes in/out processor, "self", 3 scaps files (def, abs, ftr), the scaps install path, and the scaps exe path
        # sync_parameters
            # this is used to "sync the contents of the ftr def abs files" across all the cores used
            # it is a for loop that applies to all the cores
            # there is a portion in the loop where it appears to replace some contents of the different SCAPS files
            # unclear precisely how this is syncing... is it slowly updating the parameters, or just making sure they all match once?
            # in theory, the ftr abs def fidles wont need to be updated, only the operating parameters should need to change...
            # unclear what the self.? does, since this would require it to already have the right values? what does self.? point at
        # copytree
         # this is a sub-function of sync_parameters
         # this is the function that actually copies a source folder or file and places it into a destination
        # run_inputs
           # seems to have an interative counter, and concatenate this counter with 'id' and 'calc_param'
           # this creates a unique index for the input/output of the runs
           # it then passes it to run_process?
        # time_inputs
            # this seems to pick some random time steps, pass it to the run_inputs file, then calculates something with the time delta
        # run_scaps_thread
           #  .
        # run_process
         # checks if there is still an item in the input que, then grabs it and pushes it to run_scaps_thread    



        # this seems to be defining several strings to represent filepaths, but using .format(ROOTDIR) to add the correct starting filepath
        # example = assign the correct Wine01, Wine02... to the start of the filepaths
        # worth noting that the first folder name here is /pv_bayes/...
        # it assigns ROOTDIR as 'HOME'

    #ROOTDIR = os.environ['HOME']
    ROOTDIR = "/trace/home/jdrew"
    SCAPS_PARAM_DEF_DIR = '{}/pv_bayes/running_sims/scaps_dat/def'.format(ROOTDIR)
    SCAPS_PARAM_ABS_DIR = '{}/pv_bayes/running_sims/scaps_dat/absorption'.format(ROOTDIR)
    SCAPS_PARAM_FTR_DIR = '{}/pv_bayes/running_sims/scaps_dat/filter'.format(ROOTDIR)
    SCAPS_INSTALL_DIR = '{}/pv_bayes/running_sims/wine_reference'.format(ROOTDIR)
#    SCAPS_EXEC_DIR = '{}/scaps_exec'.format(ROOTDIR)
    SCAPS_EXEC_DIR = '{}/pv_bayes'.format(ROOTDIR)
        ##################################################################################################################


        # the 2nd line below has the xvfb-run wine + filepath.exe
        # removed the apostrophes from Program Files (x86)
    SCAPS_ROOT = "#/drive_c/Program Files (x86)/Scaps3309"
    #SCAPS_CMD = "WINEDEBUG=-all WINEPREFIX=# WINEARCH=win32 xvfb-run -a wine #/drive_c/Program Files (x86)/Scaps3309/scaps3310.exe"
    SCAPS_CMD = "WINEDEBUG=-all WINEPREFIX=# xvfb-run -a wine #/drive_c/'Program Files (x86)'/Scaps3309/scaps3310.exe"




        # """ ~~~~~~~~~~~~~~~~~~~~~ __Init__ ~~~~~~~~~~~~~~~~~~~~~ """

        # this is actually giving commands to scaps itself?
    def __init__(self,
                 input_processor,
                 output_processor,
                 ncores = MAX_CORENUM,
                 scaps_param_def_dir=SCAPS_PARAM_DEF_DIR,
                 scaps_param_abs_dir=SCAPS_PARAM_ABS_DIR,
                 scaps_param_ftr_dir=SCAPS_PARAM_FTR_DIR,
                 scaps_install_dir=SCAPS_INSTALL_DIR,
                 scaps_exec_dir=SCAPS_EXEC_DIR):
        """
        Initialize the SCAPS parallel processor.

        input_processor: a python method that takes in a dictionary of run parameters and outputs a string corresponding
                         to a SCAPS input script

        output_processor: a python method that takes a path to a SCAPS output file and returns a python object
                          representation of the output

        ncores: number of processes used to run
        """

        # unclear why it is doing this, but it seems to be using the self. command to just redefine every variable as itself?       
        self.ncores = ncores
        if ncores > self.MAX_CORENUM:
            raise ValueError("Number of cores exceeds MAX_CORENUM={}. Either modify the " + \
                             "limit, or use fewer cores".format(SCAPSrunner.MAX_CORENUM))
        self.input_processor = input_processor
        self.output_processor = output_processor
        self.scaps_param_def_dir = scaps_param_def_dir
        self.scaps_param_abs_dir = scaps_param_abs_dir
        self.scaps_param_ftr_dir = scaps_param_ftr_dir
        self.scaps_install_dir = scaps_install_dir
        self.scaps_exec_dir = scaps_exec_dir



        """ ~~~~~~~~~~~~~~~~~~~~~ Sync_Parameters / Copytree ~~~~~~~~~~~~~~~~~~~~~ """

        # comment below indicates that it syncs all of the ref def and abs directories, unclear what this implies
    def sync_parameters(self):
        """
        Syncs the contents of the reference def and absorption directories with all SCAPS execution proc folders. Does
        not modify the refence VM however.
        """

        # is this defining its own function called copytree? seems to have as inputs both a source and destination filepath
        # this block is the only appearances of copytree
        # this "copytree" is its own function, but the built-in python function "shutil" also has a subfunction called shutil.copytree
        # shutil.copytree will make a copy of an entire folder somewhere new
        # shutil.copy2 will copy a specific file to a new location (and also try to save metadata)
        # symlinks creates a symbolic link between a path... wont dive too deep into this yet
        def copytree(src, dst, symlinks=False, ignore=None):
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dst, item)
                print(f"s: {s}")
                print(f"d: {d}")
                if os.path.isdir(s):
                    shutil.copytree(s, d, symlinks, ignore)
                else:
                    shutil.copy2(s, d)

            # lines below target specifically ONE of the many cores that fall within itself
            # lines below accomplish this USING the copytree function defined above
            # targets the scaps_param_def_dir of itself as the "src" argument, then replaces something with it?
            # does this again for abs and ftr files
            # what is "core" referenced below?
                # core is referencing the actual core that the job is running on
                # this will take the core's def abs and ftr files and do something to them...
                # replacing something in all the files somehow
        for core in range(self.ncores):

            copyfrom = self.scaps_param_def_dir
            copyto = "{}/def".format(self.SCAPS_ROOT.replace('#','{}/proc{}'.format(self.scaps_exec_dir, core)))
            print("copying the things from" + copyfrom + " to " + copyto)
            copytree(self.scaps_param_def_dir,
                     "{}/def".format(self.SCAPS_ROOT.replace('#','{}/proc{}'.format(self.scaps_exec_dir, core))))
            copytree(self.scaps_param_abs_dir,
                     "{}/absorption".format(self.SCAPS_ROOT.replace('#','{}/proc{}'.format(self.scaps_exec_dir, core))))
            copytree(self.scaps_param_ftr_dir,
                     "{}/filter".format(
                         self.SCAPS_ROOT.replace('#', '{}/proc{}'.format(self.scaps_exec_dir, core))))




            """ ~~~~~~~~~~~~~~~~~~~~~ Run_Inputs ~~~~~~~~~~~~~~~~~~~~~ """
            # not yet a complete understanding of this, need to circle back
    def run_inputs(self, inputs, print_progress=True):
        """
        Process SCAPS run parameters in parallel. Takes in a dictionary of inputs, structured as
        {'id1':run_params_1, 'id2':run_params_2, ...}
        where run_params_1, run_params_2, ... should be the argument to the pre-specified input processor method.

        Returns a dictionary structured as
        {'id1':output_1, 'id2':output_2, ...}
        where output_1, output_2, ... are the objectrs returned by the pre-specified output processor method
        """

        # defines inq and outq as some predefined function "Queue()" (imported with Multiprocessing)
        inq = Queue()
        #print(f"inq: {inq}")
        outq = Queue()
        #print(f"outq: {outq}")
        # unclear what this variable defining as {} means        
        output_dict = {}
        # this creates a variable num_total that is the length of the input.keys()
        # then defines an initial variable "num_done"=0
        # likely, this is a defining an initial and final counter variable, to know how many iterations of this loop need to be run        
        num_total = len(inputs.keys())
        num_done = 0

        proc_list = []

        # SCAPS_ROOT is a filepath defined at the very start of the code (...drive_c/Program Files/Scaps3309...)
        # unsure what config_all does        
        config_all = {'SCAPS_ROOT':self.SCAPS_ROOT, 'SCAPS_CMD':self.SCAPS_CMD,
                      'SCAPS_EXEC_DIR':self.scaps_exec_dir, 'INPUT_PROC':self.input_processor,
                      'OUTPUT_PROC':self.output_processor}
        # runs a loop through all the cores in the desired range
        # assigns the string 'CORE' to the specific core being used (proc_i)
        # calls the pre-defined "Process()"
        for proc_i in range(self.ncores):
            config_proc = deepcopy(config_all)
            config_proc['CORE'] = proc_i
            #print(f"config_proc[CORE]: {config_proc['CORE']}")
            #print(f"proc_i: {proc_i}")
            #even with only 3 sets of parameters, these generate over 30 cores and procs
            proc = Process(target=SCAPSrunner.run_process, args=(config_proc, inq, outq))
            proc.start()
            proc_list.append(proc)
            #print(f"proc_list: {proc_list}")

        # seemingly tries to modify the input queue that was defined as the variable "inq"?
            # uses the sting "id" which was previously associated with a certain number of the input and output values
            # (id1 is associated with params1 and output1)
        # the orange and yellow section below ('id':id, 'calc_param':input) seems to be joining a string with some iterative counter
            # this is likely the counter inputiter
        inputiter = iter(inputs.items())
        print(f"inputiter: {inputs.items()}")
        while True:
            #print("entered True loop")
            running = any(proc.is_alive() for proc in proc_list)
            if not running:
                break
            while inq.empty():
                #print("entered inq.empty loop")
                try:
                    #print('trying...')
                    (id, input) = next(inputiter)
                    inq.put({'id':id,'calc_param':input})
                except:
                    #print("entered inq empty except group")
                    inq.put({'id':'done'})


            while not outq.empty():
                pt = outq.get()
                print(f"pt: {pt}")
                output_dict[pt['id']] = pt['output']
                num_done += 1
                if print_progress:
                    print("Finished input ID{} [{}/{} total]".format(pt['id'], num_done, num_total))

        for proc_i, proc in enumerate(proc_list):
            proc.join()


        # this section just handles when one of the cores is finishing its calculation while the others are finished and waiting to end
        # Garbage collect
        while not inq.empty():
            inq.get()
        while not outq.empty():
            outq.join()
        # Give queues time to close
        time.sleep(5)

        # this just checks whether the size of the input array matches the size of the output array
        if not (set(inputs.keys())==set(output_dict.keys())):
            print("Warning: Not all inputs seem to have gotten outputs")

        # this then outputs whatever the output matrix/file is
        return output_dict
        #return "zzzzzz"



        """ ~~~~~~~~~~~~~~~~~~~~~ Time_Inputs ~~~~~~~~~~~~~~~~~~~~~ """

        # this is the only instance of time_inputs appearing in the code, so standalone function?
        # defines sample_size as 216... maybe 216-entry vector of "time"?
    def time_inputs(self, inputs, sample_size=216):
        sample_inputs = {}

        # line below is defining the varibale "ids" as a list from input.keys()...
        # then, it randomly samples this variable?

        ids = list(inputs.keys())
        random.shuffle(ids)
        for sample in range(sample_size):
            sample_inputs[ids[sample]] = inputs[ids[sample]]

        # for some reason this function also calls a start time and end time of doing the actual run?
        # it also then takes the time delta and divides it by the sample size...
        startTime = time.time()

        # once these time values are chose, it uses the above function "run_inputs" on the chose sample times?        
        self.run_inputs(sample_inputs, print_progress=True)
        endTime = time.time()
        return (endTime-startTime)/sample_size




        """ ~~~~~~~~~~~~~~~~~~~~~ Run_Scaps_Thread ~~~~~~~~~~~~~~~~~~~~~ """

        # says it "runs scaps on a single thread" but this is likely happening on many threads in parallel
        # the scaps executions 'needs a config directory and a parameters dictionary'
        # these are likely provided by all the auxiliary functions so far
        # arguments passed are "config" and "run_params"
            # neither of these two arguments are functions that are defined in the superstructure of this code
        # this is the portion that writes the scaps input text file and obtains the scaps output

    @staticmethod
    def run_scaps_thread(config, run_params):
        print("called run_scaps_thread")
        """
        Executes SCAPS on a single thread. Needs a configuration dictionary and a run_parameters dictionary. """
        # this is the portion that writes the scaps input text file and obtains the scaps output
        """ The config dictionary specifies the directories where SCAPS is running, the commands needed to launch it, the
        process number (which VM is running this process), an 'INPUT_PROC' field specifying a python method that can
        take the run parameters and generate a SCAPS input script, and an 'OUTPUT_PROC' field specifying a python
        method that can take a SCAPS output and generate a python object representation of it. """

        # like this aludes to, there are two variables (id, calc_params) that are followed by a unique number to serve as a reference
        """ The run_params dictionary has two fields - 'id' which uniquely identifies this run, and 'calc_params', which
        are the arguments passed to the input_processor to generate the SCAPS inputs for this run.
        """

        # the python script is always called 'pythonscript.script', but unclear exactly what it does so far
        """
        For the purposes of the script generator, the python runscript is always called 'pythonscript.script' and the
        output file is always called 'pythonresult.txt'
        """
        # this seems to just concatenate different file path names
        # so, this is probably related to directing either a file to be read or to be saved?        
        script_name = "pythonscript.script"
        script_dir = os.path.join(config['SCAPS_ROOT'].replace('#','{}/proc{}'.format(config['SCAPS_EXEC_DIR'], config['CORE'])), 'script')
        script_file = os.path.join(script_dir, script_name)
        # this set of 3 lines seems to just be defining "script_file" as the directory + "pythonscript.script"

        # this set of 3 below similarly seems to be concatenating the directory with the name of some result file (will get overwritten?)
        result_name = "pythonresult.txt"
        result_dir = os.path.join(config['SCAPS_ROOT'].replace('#','{}/proc{}'.format(config['SCAPS_EXEC_DIR'], config['CORE'])), 'results')
        result_file = os.path.join(result_dir, result_name)

        # unsure what happens below
        # if nothing else, can see that it writes to a text file, skips a line, tells scaps to "save results.iv", then skips to new line

        script = config['INPUT_PROC'](run_params['calc_param']) + "\nsave results.iv {}\n".format(result_name)
        with open(script_file,"w") as fout: fout.write(script)

        # 
        cmd = config['SCAPS_CMD'].replace('#','{}/proc{}'.format(config['SCAPS_EXEC_DIR'], config['CORE'])) + " " + script_name
        print("calling command: " + cmd)
        subprocess.call(config['SCAPS_CMD'].replace('#','{}/proc{}'.format(config['SCAPS_EXEC_DIR'], config['CORE'])) + " " + script_name, shell=True)
        # append marker to end of file for easy parsing
        with open(result_file, 'a') as f:
            f.write("I have deduced that this is the end")
        return {'id':run_params['id'], 'output': config['OUTPUT_PROC'](result_file)}




        """ ~~~~~~~~~~~~~~~~~~~~~ Run_Process ~~~~~~~~~~~~~~~~~~~~~ """

    @staticmethod
    def run_process(config, inputs, outq):

        print(f"entered run process with input: {inputs}")
        #print(f"run process config: {config}")
        #print(f"config_proc: {config_proc}")
        #print(f"config_proc: {config_all}")

        """
        Runs a thread that pulls inputs from the input queue and calls the SCAPS thread processor to get an output.
        Terminates when it receives an input with the id 'done'. The config dictionary is defined analogously to that
        detailed in run_scaps_thread, while the inputs queue gives a pointer to the root-level queue that distributes
        SCAPS inputs to the various running processes.
        """

        # this seems to go to some designated "input" queue using inputs.get(), then assign the obtained "input"  as the variable "param"
        # this presumably means the input is the set of parameters that the next scaps simulation should be run at
        # this may be related to joblib? the "inputs.empty()" thing doesn't seem to have to be defined explictly in this code
        # this also means that somehow in the list of inputs, the final entry in the vector must the the string 'done' to signal end
        # as long as there are still inputs to run, it uses the function above (run_scaps_thread), but passes it an argument of "param"
        # worth noting that this may just be moving through PARAMTER space (PS), rather than EXPERIMENTAL space (ES)
        # possible that "param" is a PS identifier, and that "config" is an ES identifier???
            # this seems less likely, since "config" is used in a more complicated way above in this script
        while True:
            #print("got to the while true inside of run_process")
            if not inputs.empty():
                print("inputs is not empty")
                param = inputs.get()
                print(param)
                if param['id'] == 'done':
                    break
                else:
                    print("inputs was empty, calling (or trying to call) run_scaps_thread")
                    outq.put(SCAPSrunner.run_scaps_thread(config, param))
        return



        # this note below was written when just starting to understand this whole python code. Think this is irrelevant
        # SCAPSrunner seems to call both config and param as arguments?
        # but this is only when using SCAPSrunner.run_scaps_thread(arg, arg)...
