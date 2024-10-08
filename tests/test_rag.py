"""Module provides test of inference results."""

import os
import sys
import model_io as mio
import logging
sys.path.insert(0, './tests')

logging.basicConfig(level=logging.INFO, filename="bot_logs/testing.log",
                    filemode="a")
LOGGER = logging.getLogger(__name__)

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


def test_gas_type():
    query = "Какой применяется бензин?"
    model_answer = mio.get_rag_context(query)

    assert "АИ-92" in model_answer
    assert "АИ-95" in model_answer


def test_gas_type_2():
    query = "Какой лить бензус?"
    model_answer = mio.get_rag_context(query)

    assert "АИ-92" in model_answer
    assert "АИ-95" in model_answer

def test_head_light():
    query = "Лампа головного света?"
    model_answer = mio.get_rag_context(query)
    LOGGER.info(model_answer)
    assert "60/55" in model_answer


def test_head_light_2():
    query = "Лампа фары?"
    model_answer = mio.get_rag_context(query)
    LOGGER.info(model_answer)
    assert "60/55" in model_answer


def test_break_liquid():
    query = "Тормозная жидкость?"
    model_answer = mio.get_rag_context(query) 
    LOGGER.info(model_answer)
    assert "DOT 4" in model_answer


def test_motor_oil_type():
    query = "Тип моторного масла?"
    model_answer = mio.get_rag_context(query) 
    LOGGER.info(model_answer)
    assert "10W40" in model_answer


def test_motor_oil_type_2():
    query = "Тип моторного масла?"
    model_answer = mio.get_rag_context(query) 
    LOGGER.info(model_answer)
    assert "API SE, SF или SG с вязкостью SAE 10W40" in model_answer


def test_seat_hight():
    query = "Высота сиденья?"
    model_answer = mio.get_rag_context(query) 
    LOGGER.info(model_answer)
    assert "810" in model_answer





