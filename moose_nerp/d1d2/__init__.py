from __future__ import print_function, division
from .param_chan import (VMIN, VMAX, VDIVS, CAMIN, CAMAX, CADIVS,
                         qfactNaF,
                         Channels)
from .param_cond import (ghKluge,
                         neurontypes,
                         ConcOut, Temp,
                         morph_file,
                         Condset,
                         NAME_SOMA)
from .param_spine import SpineParams
from .param_syn import (SYNAPSE_TYPES,
                        NumSyn,
                        DesensitizationParams,
)

from . import param_ca_plas as CaPlasticityParams
from .param_stim import Stimulation
import logging

from moose_nerp.prototypes import (create_model_sim,
                                   constants)

#calcium: include or exclude calcium concentration dynamics, single tau
#synYN:No point adding synapses unless they receive inputs
#plasYN:include or exclude plasticity based on calcium

plasYN = False
desenYN = False
ghkYN = False
spineYN = False
synYN = False
calYN = True

#note that if ghkYN=0, make sure that ghKluge = 1
