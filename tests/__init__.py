################################################################################
# tests/__init__.py
################################################################################

from tests.test_LABEL_GRAMMAR import *
from tests.test_vicarlabel    import *
from tests.test_vicarimage    import *

##########################################################################################
# Perform unit testing if executed from the command line
##########################################################################################

if __name__ == '__main__':
    unittest.main()

##########################################################################################
