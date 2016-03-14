import os.path
import sys

# If we are working on a development version of IDLE, we need to prepend the
# parent of this idlesporklib dir to sys.path.  Otherwise, importing idlesporklib gets
# the version installed with the Python used to call this module:
idlesporklib_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, idlesporklib_dir)

import idlesporklib.PyShell
idlesporklib.PyShell.main()
