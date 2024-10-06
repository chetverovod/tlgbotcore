"""Module provides test of inference results."""

import os
import sys
import model_io as mio
sys.path.insert(0, './tests')


def test_valve_gap():

    query = "Зазор клапанов?"
    model_answer = mio.get_rag_context(query)

    assert "0.1" in model_answer


def test_gas_tank():

    query = "Емкость топливного бака?"
    model_answer = mio.get_rag_context(query)

    assert "13" in model_answer


def test_chain_links_count():

    query = "Длина цепи?"
    model_answer = mio.get_rag_context(query)

    assert "112" in model_answer


def test_chain_checkin():

    query = "Как проверить состояние цепи?"
    model_answer = mio.get_rag_context(query).lower()

    assert "ржав" in model_answer
    assert "перекрученные" in model_answer
