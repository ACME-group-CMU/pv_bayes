#!/usr/bin/env python

from __future__ import unicode_literals, division

__author__ = "Rachel Kurchin, Riley Brandt, Daniil Kitchaev, and JDrew"
__date__ = "May 17, 2017"

from run_scaps_parallel import SCAPSrunner
import numpy as np
from copy import deepcopy
import pickle
import os
import argparse
import json



""" ~~~~~~~~~~~~~~~~~~~~~ Scaps_Output_Processor ~~~~~~~~~~~~~~~~~~~~~ """

# this might be defining the output of a scaps run as the variable "return_path", to then pull data from it later and assign it
def scaps_output_processor(return_path):
    """
    Convert output of a SCAPS simulation to a numpy format for further processing
    """
    # this line just defines these 4 variables as 0 (the start of a counter), and 3 empty matrices?
    # the ii counter is redefined as +1 to its original value at the end of the loop?
    ii, simList, summaryList, dataLines = 0, [], [], []
    
    # this opens the scaps file "return_path", then grabs the data from certain line strings
    # it will add any line that says 'jtot' to the ii'th entry in the vector simList
    # it will add any line that says 'deduced' to the ii'th entry in the vector summaryList
    # it will then increment ii by 1
    with open(return_path,'r') as f:
        for line in f:
            if 'jtot' in line: simList.append(ii)
            elif 'deduced' in line: summaryList.append(ii)
            ii += 1

    #this appears to be adding some new value to the end of the 'datalines' matrix variable
    for xi, x in enumerate(simList):
        dataLines.extend(list(range(x + 2, summaryList[xi] - 3))) # TODO: check that -3 is right and isn't truncating data

    #defines the two variables as matrices full of zeros, to the length of the datalines variable
    JArray, VArray = np.zeros(len(dataLines)), np.zeros(len(dataLines))

    #resets the counter variable to zero
    #unclear why do this, because it defines jj as opposed to ii?
    ii = 0
    #    
    with open(return_path,'r') as f:
        for jj, line in enumerate(f):
            if jj in dataLines:
                floats = [float(x) for x in line.split("\t")]
                JArray[ii] = floats[1]
                VArray[ii] = floats[0]
                ii += 1

    return (JArray, VArray)



    """ ~~~~~~~~~~~~~~~~~~~~~ Scaps_Script_Generator ~~~~~~~~~~~~~~~~~~~~~ """

    # this section seems to involve creating a text file (scaps script generation) that will define all the commands we want to send to scaps
def scaps_script_generator(calc_param):
    """
    Generate SCAPS simulation input script as a string.
    """
 
    # closes scaps when done
    # ?
    # 
    # 4 lines deffining the physical system being modeled (layers, interfaces)
    # several lines defining the operating conditions being evaluated (experimental space)
        # temperature set to the value of the entry in variable matrix calc_param[T_1]
        # 3 lines on voltage that set the bounds and step size of the voltage
        # intensity is also set equal to the entry of the illumination matrix
    # final line 
    print(f"calc param: {calc_param}")
    return "\n".join(["//Script file made by Python",
                       "set quitscript.quitSCAPS",
#                       "load allscapssettingsfile {}".format(calc_param['def']),
                        "load definitionfile {}".format(calc_param['def']),
                       "set errorhandling.overwritefile",
#                       "set layer1.mun %f" % calc_param['mu_n_l'],
#                       "set layer1.defect1.Ntotal %f" % calc_param['Nt_SnS_l'],
#                       "set layer2.chi %f" % calc_param['EA_ZnOS_l'],
#                       "set interface1.IFdefect1.Ntotal %f" % calc_param['Nt_i_l'],
                       "action workingpoint.temperature %f" % calc_param['T_l'],
                        "action intensity.T %f" % calc_param['ill_l'],
                        "action iv.startv %f" % 0.0,
                        "action iv.stopv %f" % calc_param['V_max'],
                        "action iv.increment %f" % 0.02,
                        "action iv.doiv",
                        "calculate"])


    # video bookmarked summarizing much of this syntax below
    # first and second lines seem to be default for defining a function
    # the 3 "parser.add_argument" lines make it so when calling this function, you need to add 3 inputs (-si, -ni, -node)
    # they seem to relate to the job tasking, so assume that these are passed to joblibs somehow for parallelization

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-si', help="Start index for this run", type=int, default=0)
    parser.add_argument('-ni', help="Number of inputs to run here", type=int, default=0)
    parser.add_argument('-node', help="Node index (proc index offset)", type=int, default=0)
    args = parser.parse_args()

    node = args.node

    # this is where scaps starts to run??? unclear
    # what does scaps_runner do? is this self defined?
    # this *actually* is a re-definition of the function SCAPSrunner, which IS in run_scaps_parallel.py code


    # Initialize SCAPS runner object
    # ncores used to be = 32
    scaps_runner = SCAPSrunner(ncores=3,
                               input_processor=scaps_script_generator,
                               output_processor=scaps_output_processor)


    """
    baseline_run = {'def': "SnS_base.scaps",
                    'mu_n_l': 60,
                    'Nt_SnS_l': 1e17,
                    'EA_ZnOS_l': 4.0,
                    'Nt_i_l': 1e10,
                    "V_max": 0.5}
    """

    baseline_run = {'def': "CdTe-base.def",
                    "V_max": 0.5}

    temperatures = np.array([280, 300, 320])  #***replaced by line below
    #temperatures = np.array([280])
    #illuminations = np.array([31, 108]) ***replaced by line below
    illuminations = np.array([108])
    #mu_n_range = np.linspace(20, 80, 20)
    #Nt_SnS_range = np.logspace(16, 18, 20)
    #EA_ZnOS_range = np.linspace(3.4, 4.3, 15)
    #Nt_i_range = np.logspace(10, 14, 16) ***replaced by line below
 #   Nt_i_range = np.array([1e14])

    inputs = {}
    i = 0


    # what does run[?] do?
    for temp in temperatures:
        for ill in illuminations:
 #           for Nt_i in Nt_i_range:
                # for mu_n in mu_n_range:
                # for Nt in Nt_SnS_range:
                # for EA in EA_ZnOS_range:
                run=deepcopy(baseline_run)
                # baseline_run['Nt_i_l'] = Nt_i
                # run['mu_n_l'] = mu_n
                # run['Nt_SnS_l'] = Nt
                # run['EA_ZnOS_l'] = EA
                run['T_l'] = int(temp)
                run['ill_l'] = int(ill)
                inputs[i] = run
                i += 1

    # input_parameters.json has 96 entries of scaps parameters for a run...
    with open("input_parameters.json", 'w') as fout:fout.write(json.dumps(inputs))

    # n_batches used to be 16
    n_batches = 1
    for batch_i in range(n_batches):
        #print(f"batch i: {batch_i}")
        batch_size = int((args.si + args.ni)/n_batches)
        #print(f"batch size: {batch_size}")
        batch_inputs = {}
        #print(f"args.si + batch_i * batch_size: {args.si + batch_i * batch_size}")
        #print(f"args.si + batch_i * batch_size + batch_size: {args.si + batch_i * batch_size + batch_size}")
        for pt_i in range(args.si + batch_i * batch_size, args.si + batch_i * batch_size + batch_size):
            #print(f"args si: {args.si}")
            #print(f"args ni: {args.ni}")
            #print(f"inputs: {inputs}")
            #print(f"inputs[pt_i]: {inputs[pt_i]}")
            
            batch_inputs[pt_i] = inputs[pt_i]
            #batch_inputs[pt_i] = inputs
            #print(f"single batch input: {batch_inputs[pt_i]}")


        #print(f"all batch inputs: {batch_inputs}")

        # Run the inputs
        print("[Batch {}] Starting SCAPS runs ({}-{})".format(batch_i, args.si + batch_i * batch_size, args.si + batch_i * batch_size + batch_size))
        outputs = scaps_runner.run_inputs(batch_inputs, print_progress=True)

        #print(f"outputs: {outputs}")

        # Save outputs
        print("[Batch {}] Saving outputs as pickles...".format(batch_i))
        pickle.dump(outputs, open("simulation_{}_{}_n{}_b{}.pickle".format(args.si + batch_i * batch_size,
                                                                           args.si + batch_i * batch_size + batch_size,
                                                                           node,
                                                                           batch_i),"wb"))
