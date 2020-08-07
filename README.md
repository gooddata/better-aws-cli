
## Better Aws Cli

### Installation
In order to install required dependencies, run following command from the project's top level directory:
			    
	pip install -r requirements
  
  #### Supported versions:
  Make sure you have at python2.7 or python3.6 or higher installed.


### Running the *Better Aws Cli*
Each AWS account that you wish to manage with the tool must have their respective authentication credentials sourced in the shared AWS *credentials* file (default location of this file is` ~/.aws/credentials`).

If you wish to use the IAM Role assumption to manage the accounts, you must set up your AWS *configuration* file accordingly (this file's default location is `~/.aws/config`).

For more information about setting up credentials and configuration files, please read [the aws-cli documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html).

To start the tool, change the current directory to the project's top-level directory and run the following command:

    python -m bac
   
Once you see the `~>` prompt show up, the tool is initialized, and you can start your work with AWS.


### Usage
The basic intended workflow is as follows:
	- Run the tool with `python -m bac`
	- Activate profiles and regions, that you wish to manage (e.g.: `include-profiles my-test-profile`)
	- Run the desired aws-cli command (e.g.: `aws s3api list-buckets`)

#### Managing profiles and regions

Several commands have been defined to help manage on which profiles and regions the called aws-cli commands get executed on. To manage profiles, you can use:

 - `include-profiles [profiles]` - includes all provided `profiles` to the set of currently active profiles.
	
- `exclude-profiles [profiles]` - exclude all provided `profiles` from the set of currently active profiles.

 - `switch-profiles [new-profiles]` - switch active profiles to `new-profiles`. Discard all previously active profiles.
 - `list-active-profiles` - lists all currently active profiles.
 
 If `--profile <profile>` is provided to the *aws-cli* command, the set of currently active profiles is disregarded, and the explicitly provided `profile` is used instead.

The same rules apply to active region management, with one exception: If no region is active (i.e., the set of currently active regions is empty), `--region "us-east-1"`  is used as the default region.

#### BAC optional arguments
By default, *BAC* provides syntax and type checking of commands before their execution.  In addition to syntax/type checking, the command can also be *privilege checked*.

In order to provide users with better control over when the syntax and privilege check is being applied to the called *aws-cli* command or *batch-command*, the tool supports three following global positional arguments:

 - `--bac-dry-run` - do not execute the command after it is checked
 
 - `--bar-no-check` - do not syntax/type check command before its execution
 
 - `--bac-priv-check` - attempt to check for sufficient privileges before executing the command

At the moment, the auto-completion of the mentioned three custom BAC optional arguments is not supported. This will change soon.

#### Batch command definitions:
Sometimes, you might want to configure, create, delete multiple AWS resources of the same type. To that end, batch-commands might be of some use to you. A batch command is essentially an aws-cli command defined with multiple different values for its optional parameters.

Batch commands need to be defined in YAML format and consist of two parts: a command section, which contains the basis of the aws-cli command to be executed, and the optionals section, which contains all of the different variations of parameter-value pairs.

If you're looking for a syntax reference of the batch command definitions (`batch-command`), try looking into the "examples" directory.


### Testing
There are two ways to run tests at the moment.

#### Tox
If you have *tox* installed, just run following command:

	tox .
One of the test environments will probably fail due to the inability to locate the correct desired version of the python interpreter. This is the expected behavior.

#### unittest
If you do not have *tox* installed, or do not wish to do so, you can tun the tests manually with *unittest*. To do so, call the following command from the project's top-level directory:

	python -m unittest discover tests

## License
(C) 2020 GoodData Corporation

This project is under commercial license. See [LICENSE](LICENSE).
