"""
Тести для нормалізації параметрів фільтрації у API роутері.
Перевіряє що функція normalize_list_param правильно обробляє різні формати.
"""

import pytest
from src.api.routers.spaces import normalize_list_param


def test_normalize_list_param_with_brackets():
    """Тест нормалізації зі списком що має дужки."""
    input_values = ["['personal']", "['global']"]
    result = normalize_list_param(input_values)
    
    # Функція видаляє дужки та лапки
    assert result == ["personal", "global"]


def test_normalize_list_param_with_quotes():
    """Тест нормалізації з лапками."""
    input_values = ['"personal"', "'global'"]
    result = normalize_list_param(input_values)
    
    assert result == ["personal", "global"]


def test_normalize_list_param_clean():
    """Тест нормалізації чистих значень."""
    input_values = ["personal", "global"]
    result = normalize_list_param(input_values)
    
    assert result == ["personal", "global"]


def test_normalize_list_param_with_spaces():
    """Тест нормалізації зі зайвими пробілами."""
    input_values = [" personal ", "  global  "]
    result = normalize_list_param(input_values)
    
    assert result == ["personal", "global"]


def test_normalize_list_param_empty():
    """Тест нормалізації порожнього списку."""
    input_values = []
    result = normalize_list_param(input_values)
    
    assert result == []


def test_normalize_list_param_with_empty_strings():
    """Тест нормалізації зі порожніми рядками."""
    input_values = ["", " ", "personal", ""]
    result = normalize_list_param(input_values)
    
    assert result == ["personal"]


def test_normalize_list_param_complex():
    """Тест нормалізації складних випадків."""
    input_values = ["['personal']", '"global"', " archived ", ""]
    result = normalize_list_param(input_values)
    
    # Перевірити що всі значення присутні та нормалізовані
    assert len(result) == 3
    assert "archived" in result
    assert "global" in result


def test_normalize_list_param_real_swagger_format():
    """
    Тест реального формату зі Swagger.
    Swagger може передавати: ['personal', 'global']
    """
    # Симулюємо що Swagger передав один елемент як строку
    input_values = ["personal", "global"]
    result = normalize_list_param(input_values)
    
    assert result == ["personal", "global"]
    assert "personal" in result
    assert "global" in result


def test_normalize_list_param_comma_separated():
    """
    Тест для comma-separated значень в одному рядку.
    Користувач вводить: "personal, global"
    """
    input_values = ["personal, global"]
    result = normalize_list_param(input_values)
    
    assert len(result) == 2
    assert "personal" in result
    assert "global" in result


def test_normalize_list_param_comma_separated_no_spaces():
    """
    Тест для comma-separated значень без пробілів.
    Користувач вводить: "personal,global,team"
    """
    input_values = ["personal,global,team"]
    result = normalize_list_param(input_values)
    
    assert len(result) == 3
    assert result == ["personal", "global", "team"]


def test_normalize_list_param_mixed_format():
    """
    Тест міксу форматів: окремі елементи + comma-separated.
    """
    input_values = ["personal, global", "archived"]
    result = normalize_list_param(input_values)
    
    assert len(result) == 3
    assert "personal" in result
    assert "global" in result
    assert "archived" in result
