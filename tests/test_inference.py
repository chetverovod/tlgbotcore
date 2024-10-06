"""Module provides test of inference results."""

import os
import sys
import model_io as mio
sys.path.insert(0, './tests')


def test_valve_gap():

    query = "Зазор клапанов?"
    model_answer = mio.make_answer(query)

    assert "0.1" in model_answer


def test_gas_tank():

    query = "Емкость топливного бака?"
    model_answer = mio.make_answer(query)

    assert "13" in model_answer


def test_chain_links_count():

    query = "Длина цепи?"
    model_answer = mio.make_answer(query)

    assert "112" in model_answer
