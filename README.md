# Running SCAPS in high throughput
This repo contains code for running SCAPS PV simulations in a Linux CLI via a Python script and [wine](https://www.winehq.org/). Many, many thanks are due to Dr. Daniil Kitchaev, who was instrumental in hacking together the original setup back in 2016-2017 (see repo that this one is forked from).

It is worth remarking that SCAPS is really not designed to be run in high-throughput, in a couple of ways: 

* It has a scripting language, but even when running in scripting mode, it insists on trying to pop up a window. This is one of the things we have to hack around to run it on an HPC system in a high-throughput way; we do so by starting a "dummy" display server so that it doesn't generate an error; it thinks it's sending the windows somewhere and we can still control the application's behavior from the script.
* It has some paths to support files etc. internally hardcoded, which means we will need to explicitly make copies of the entire set of files and run them in separate wine instances to avoid things overwriting themselves when we try to run in parallel. This is about a gigabyte of files, so it's not insignificant, but it's not the end of the world since we can do all the copying once before we launch things and then reuse each one serially.

This code is provided under the MIT license.

I will attempt to document how to set everything up from scratch as of December 2022 in case we ever need to do it again; in practice many of this steps will not have to be performed regularly.

## Setting up reference wine files
The first step to generate a SCAPS install and its associated support files. This is what I needed to do on my macOS 12.6 machine; if you are running a Unix-based machine that supports wine natively, the Docker cludgery is not necessary.

1. Install and launch [Docker](https://www.docker.com/products/docker-desktop/).
2. Download [docker-wine](https://hub.docker.com/r/scottyhardy/docker-wine/):
    ```
    curl -O https://raw.githubusercontent.com/scottyhardy/docker-wine/master/docker-wine
    chmod +x docker-wine
    ```
3. Download the [SCAPS](https://scaps.elis.ugent.be/) source files, place them inside a directory (I will assume it is called `SCAPS/` henceforth). Create a subdirectory where the wine files will live; I'm calling that `SCAPS/wine_stuff/`.
4. Start the docker-wine instance with root privileges and access to that directory (fill in your path appropriately) as a volume (here I've creatively named it `scaps`): `./docker-wine --as-root --force-owner --volume=/path/to/SCAPS:/scaps`. You will now be in a new shell inside of the Docker container.
5. Install the fake display driver things:
    ```
    apt update
    apt-get install xvfb x11vnc xserver-xorg-video-dummy
    ```
6. Install SCAPS in the subdirectory we created by utilizing the `WINEPREFIX` variable (note we also have to specify 32-bit architecture mode; SCAPS is oooold): `WINEPREFIX=/scaps/wine_stuff WINEARCH=win32 wine /scaps/scaps3310/setup.exe` (click through all the default options in the installer window that pops up; you will have to explicitly accept the license agreement. You can also fix the fact that the default version number is wrong (3309 instead of 3310) in the install location; this is not crucial though).

Hooray! Now we have a set of reference files with a SCAPS installation! (You can confirm this by starting up docker-wine again and, inside it, running `WINEPREFIX=/scaps/wine_stuff WINEARCH=win32 wine /scaps/wine_stuff/drive_c/Program\ Files/Scaps3309/scaps3310.exe` (or with the 3309 fixed if you did that, this is what the path will be with all the defaults))

## Running a single simulation
A useful place to start before we get into the high-throughput parallel execution stuff is making sure we can run a single simulation. We'll do this without any of the Python machinery, just straight from the command line, step by step.

**NOTE:** Henceforth, this all should be possible inside docker-wine AS WELL AS on TRACE using a set of the created `wine_stuff` files as described above. You will have to modify the paths accordingly in either case.

First, save a copy of `simple_script.script` into the `script/` subdirectory inside the `Scaps3309/` directory (where `scaps3310.exe` was installed). Then, run:

```bash
WINEDEBUG=-all WINEPREFIX=/path/to/wine_stuff WINEARCH=win32 xvfb-run -a wine /path/to/wine_stuff/drive_c/Program\ Files/Scaps3309/scaps3310.exe simple_script.script
```
This will open SCAPS (with the GUI piped to the virtual X buffer), run the script (which simply calculates an IV curve for a basic CdTe device), and save it. The output file should appear in the `results/` subdirectory within the `Scaps3309/` directory.


## Creating execution WINE emulators for SCAPS

Now create a folder that will contain the execution VMs for SCAPS, each a clone of the reference setup. There needs to be enough of these for all the threads you want to run - in this example, there will be 32, each in a folder called proc0, proc1, ..., proc31
```
$:~# mkdir $HOME/scaps\_exec
$:~# for i in \`seq 0 31\`; do cp –r $HOME/pv\_bayes/running\_sims/wine\_reference $HOME/scaps\_exec/proc$i; done`
```


# Foward simulations: Running SCAPS in parallel
SCAPS can be run through a python script once the dummy x-server is running or xvfb is set up.

To start the simulation, you need to write a small script, based on the example provided (run\_forward\_simulations.py), although its a good idea to first try a smaller set of simulations. The general structure of the run is as such:

1. Create a dictionary of input parameters, where each set of parameters has a unique id assigned to it:
`inputs = {id1: params1, id2: params2, …}`

2. Create a python method that will take one set of inputs (such as params1), and return a string corresponding to a SCAPS input script – see scaps\_script\_generator()

3. Create a python method that will take a filepath pointing to the SCAPS output file, read it in, and return some sort of python representation of the output – see scaps\_output\_processor()

4. Create a SCAPSrunner object, specifying the input and output processor functions you just wore and the number of cores you would like to use (this shouldn’t exceed the number of VM folders you created earlier – in this example, this is 32)

5. Sync the def and absorption files to the run directories by calling the sync\_parameters() method. The contents of the reference def/ and absorption/ directories (currently pv\_bayes/scaps\_dat/def and pv\_bayes/scaps\_dat/absorption) will then go to all the VMs.

6. Run SCAPS in parallel over all the inputs you specified by calling the run_inputs(inputs) method. The outputs are returned as a dictionary with the outputs labelled by the same ids as you had in the inputs:
outputs = {id1: output1, id2: output2, …}

Finally, to run the script you just wrote (or the example script), you need to tell python to use the dummy graphics driver, so as to suppress the SCAPS GUI. The run command is:

$:~# cd ~/pv\_bayes/running\_sims
$:running\_sims# DISPLAY=:99 python run\_forward\_simulations.py

where the DISPLAY=:99 section is not necessary if using xvfb.

A useful function is the time\_inputs(inputs) function – it takes a random sample of the input parameters and estimates the average amount of time per SCAPS run this simulation will take, allowing you to estimate the total amount of time it will take to run through all the parameters. You can see a usage example in run\_forward\_simulations.py

After the simulations are done, there will be a folder called pickles containing the raw outputs of all the simulations.

In the current implementation of run\_forward\_simulations.py, runs are batched by several parameters, saving run outputs several times through the simulation. In general, this should be automated based on the type of computational resources available, scheduling and queuing system, etc. Currently, these batched outputs need to be combined after the fact into a single datafile, using process\_pickles.py:

$:~# cd ~/pv\_bayes/running\_sims
$:running\_sims# python process_pickles.py

# Bayesian inference
The outputs of the simulations first need to be batched together for easier processing - the process\_pickles.py script takes care of this step, but can take a long time.

After the data is batched together, the Bayesian inference is implemented in analysis/bayes.py. The code assumes that you create a folder inside pv\_bayes/analysis called observation\_data that contains experimental JVTi data with the first row being column headers, followed by JVTi data in space-delimited format. See read_obs() in bayes.py for details.

$:~# cd ~/pv\_bayes/analysis
$:analysis# python bayes.py

After the code is run, there will be a folder called probs that will contain the probabilities obtained for each parameter based on each observation. These probabilities can be further processed into entropies using entropy.py

$:~# cd ~/pv\_bayes/analysis
$:analysis# python entropy.py


