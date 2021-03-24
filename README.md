# redant

Design Doc Link : [Gluster-test Design-doc](https://docs.google.com/document/d/1D8zUSmg-00ey711gsqvS6G9i_fGN2cE0EbG4u1TOsaQ/edit?usp=sharing)

### Structure:

redant_libs: consists of the libs and ops that will help in running the test cases.<br>
tests: holds the test cases. Add any new test cases here.<br>

### To start Working:

1. Clone redant repo.

2. Populate the conf.yaml with relevant server and client details..


### STEP-BY-STEP procedure to run:
1. git clone `[your fork for this repo]`
2. Create a virtual environment : `virtualenv <virtual_env_name>`
3. Activate the virtual-env : `source <virtual_env_name>/bin/activate`
4. cd `[the-fork]`
5. Run `pip3 install -r requirements.txt`
6. To run the sample TC, just run the below cmd after populating the
config file with relevant values.
`python3 redant_test_main.py -c parsing/config.yml -t tests/example/`
7. Log files can be found at /tmp/redant.log [ default path ].
For more options, run `python3 redant_test_main.py --help`

The logging is specific to a TC run. So when a user gives a specific base dir
for logging when invoking `redant_test__main.py`, that directory will inturn
contain the following dirs,
 -> functional
 -> performance
 -> example

Now, based on the invocation, directory of a component will be created inside
the functional and performace dirs. And inside the component directory,
the Test case specific directory will be created which inturn will contain
volume specific log files.
So for example to see the log files of a test case which is,
`tests/functional/glusterd/test_sample_glusterd.py`
one would have to go to the directory,
`<base_log_dir>/functional/glusterd/test_sample_glusterd/`, which will inturn
contain the log files specific to volume type.
