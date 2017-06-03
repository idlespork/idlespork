IdleSpork
=========

IdleSpork is an extension of python's IDLE.

The main features include:

* Background jobs
* Running shell commands directly from IdleSpork
* Getting help by typing "?"
* Printing source code by typing "??"
* Persistent history (across multiple sessions)
* Spelling and import suggestions

Commands
--------

IdleSpork supports the following commands:

* ``jobs``
* ``kill``
* ``cd``
* ``open``

To print help for a command, type "``<command> -h``".


Control-Z (background jobs)
---------------------------

After running a jobs that takes a lot of time, you can press Control-Z. This
will move your job to the background and return to the prompt immediately,
with the same global scope (meaning all variables and functions are there).
The following line will be printed::

    **** [0] ....... - Background ****

The number ``[0]`` is the Job ID, you will need it to get the results of the job.

When your job is done, you will get the message::

    **** [0]  Done ****

The command ``jobs`` gives you access to all the jobs you sent.
Without arguments ``jobs`` will print all the running jobs.
``jobs -a`` prints all jobs (including the dead ones).
``jobs -o<jobid>`` prints the output of a job.
The output of a job can be accessed using ``Jobs[jobid].getoutput()``.
The return value of your job (which is normally save into '``_``') can be accessed
using ``Jobs[jobid].ret``.

The Jobs variable: this variable manages all jobs. Everything you can do
using the commands, you can also do using this variable.
If you lose this variable use can run: ``jobs -gJobs`` to restore it.


Shell Commands
==============

IdleSpork gives you the ability to run shell programs directly from your python
interpreter. For example, you can run ``ls``, ``cat``, ``sysinfo`` and so on.
In order to run a command, type '!' and then type your command.
IdleSpork also allows you to store the output of a command into a variable. For
example::

    x = !ls -l

will store the results of ``ls -l`` into the variable ``x``.

Note:

* DON'T use this feature to run tty commands (``vim``, ``top``, ...).
* Currently there is no input support for shell commands.

