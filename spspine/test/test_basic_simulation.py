import moose
from spspine import (cell_proto,
                     create_network,
                     inject_func,
                     tables,
                     param_syn)

import pytest

@pytest.yield_fixture
def remove_objects():
    print ("setup before yield")
    yield
    print ("teardown after yield")
    for i in ('/data', '/pulse', '/D1', '/D2', '/library'):
        try:
            moose.delete(i)
        except ValueError:
            pass

@pytest.mark.parametrize("calcium", ["", "calcium"])
@pytest.mark.parametrize("synapses", ["", "synapses"])
@pytest.mark.parametrize("spines", ["", "spines"])
@pytest.mark.parametrize("ghk", ["", "ghk"])
@pytest.mark.parametrize("plasticity", ["", "plasticity"])
@pytest.mark.usefixtures("remove_objects")
def test_single_injection(calcium, synapses, spines, ghk, plasticity):
    "Create the neuron and run a very short simulation"

    if ghk and not hasattr(moose, 'GHK'):
        pytest.skip("GHK is missing")

    MSNsyn,neuron,capools,synarray,spineHeads = \
        cell_proto.neuronclasses({'calYN':bool(calcium),
                                  'plasYN':bool(plasticity),
                                  'ghkYN':bool(ghk),
                                  'spineYN':bool(spines),
                                  'synYN':bool(synapses)},
                                 False,
                                 param_syn.SYNAPSE_TYPES,
                                 param_syn.NumSyn)

    pg = inject_func.setupinj(0.02, 0.01, neuron)
    pg.firstLevel = 1e-8

    data = moose.Neutral('/data')

    vmtab,catab,plastab,currtab = \
        tables.graphtables(neuron, False, 'getGk', capools, {}, {})

    moose.reinit()
    moose.start(0.05)

    vm1 = vmtab[0][0].vector
    vm2 = vmtab[1][0].vector

    # Quick sanity check that the values are not outlandish.
    # We do not check at the beginning because of the initial fluctuation.
    exp = (0.174
           - 0.025 * bool(spines)
           - 0.043 * bool(calcium))

    assert exp - 0.01 < vm1[250] < exp + 0.02
    assert exp - 0.01 < vm2[250] < exp + 0.02

    assert -0.01 < vm1[499] < 0.05
    assert -0.01 < vm2[499] < 0.05

@pytest.mark.parametrize("calcium", ["", "calcium"])
@pytest.mark.parametrize("synapses", ["", "synapses"])
@pytest.mark.parametrize("spines", ["", "spines"])
@pytest.mark.parametrize("single", ["", "single"])
@pytest.mark.parametrize("ghk", ["", "ghk"])
@pytest.mark.parametrize("plasticity", ["", "plasticity"])
@pytest.mark.usefixtures("remove_objects")
def test_net_injection(calcium, synapses, spines, single, ghk, plasticity):
    "Create the neuron and run a very short simulation"

    pytest.skip("skipping network tests")

    if ghk and not hasattr(moose, 'GHK'):
        pytest.skip("GHK is missing")

    if spines and not single:
        pytest.skip("spines are too much with multiple neurons")

    MSNsyn,neuron,capools,synarray,spineHeads = \
        cell_proto.neuronclasses({'calYN':bool(calcium),
                                  'plasYN':bool(plasticity),
                                  'ghkYN':bool(ghk),
                                  'spineYN':bool(spines),
                                  'synYN':bool(synapses)},
                                 False,
                                 param_syn.SynChannelParams,
                                 param_syn.NumSyn)

    MSNpop, SynPlas = \
        create_network.CreateNetwork('/input', calcium, plasticity, single,
                                     spineHeads, synarray, MSNsyn, neuron)

    pg = inject_func.setupinj(0.02, 0.01, neuron)
    pg.firstLevel = 1e-8

    data = moose.Neutral('/data')

    vmtab,catab,plastab,currtab = \
        tables.graphtables(neuron, False, 'getGk', capools, {}, {})

    moose.reinit()
    moose.start(0.05)

    vm1 = vmtab[0][0].vector
    vm2 = vmtab[1][0].vector

    # Quick sanity check that the values are not outlandish.
    # We do not check at the beginning because of the initial fluctuation.
    assert 0.15 < vm1[250] < 0.25
    assert 0.15 < vm2[250] < 0.25
    assert 0.00 < vm1[499] < 0.05
    assert 0.00 < vm2[499] < 0.05
    return vm1, vm2
