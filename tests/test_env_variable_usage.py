"""
Тест для перевірки використання старих whitelist-змінних у коді.

Перевіряє, чи використовуються в src/ такі змінні:
- ALLOWED_TAGGING_PAGES
- SUMMARY_AGENT_TEST_PAGE
- TAGGING_AGENT_TEST_PAGE
- CLASSIFICATION_AGENT_TEST_PAGE
- QUALITY_AUDIT_AGENT_TEST_PAGE
"""

import os
import re
from pathlib import Path


# Змінні для перевірки
VARIABLES_TO_CHECK = [
    "ALLOWED_TAGGING_PAGES",
    "SUMMARY_AGENT_TEST_PAGE",
    "TAGGING_AGENT_TEST_PAGE",
    "CLASSIFICATION_AGENT_TEST_PAGE",
    "QUALITY_AUDIT_AGENT_TEST_PAGE"
]


def search_variable_usage(variable_name: str, src_dir: Path) -> dict:
    """
    Шукає використання змінної в коді.
    
    Args:
        variable_name: Назва змінної
        src_dir: Директорія для пошуку
    
    Returns:
        {
            "found": bool,
            "files": list,
            "patterns_found": list
        }
    """
    patterns = [
        rf'settings\.{variable_name}',  # settings.VARIABLE
        rf'os\.getenv\(["\']?{variable_name}["\']?\)',  # os.getenv("VARIABLE")
        rf'_env\(["\']?{variable_name}["\']?\)',  # _env("VARIABLE")
        rf'getenv\(["\']?{variable_name}["\']?\)',  # getenv("VARIABLE")
        rf'environ\[["\']?{variable_name}["\']?\]',  # environ["VARIABLE"]
        rf'config\.{variable_name}',  # config.VARIABLE
    ]
    
    found_in_files = []
    patterns_found = []
    
    # Пошук у всіх Python файлах
    for py_file in src_dir.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                for pattern in patterns:
                    if re.search(pattern, content):
                        found_in_files.append(str(py_file))
                        patterns_found.append(pattern)
                        break  # Достатньо знайти одне входження в файлі
        except Exception as e:
            print(f"Warning: Could not read {py_file}: {e}")
    
    return {
        "found": len(found_in_files) > 0,
        "files": list(set(found_in_files)),
        "patterns_found": list(set(patterns_found))
    }


def test_env_variable_usage():
    """
    Тест перевіряє що старі whitelist-змінні НЕ використовуються в коді.
    
    Після міграції на WhitelistManager ці змінні більше не потрібні.
    Тест падає якщо знайдено використання будь-якої з цих змінних.
    """
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    
    if not src_dir.exists():
        raise FileNotFoundError(f"Directory {src_dir} not found")
    
    results = {}
    used_variables = []
    
    print("\n" + "="*70)
    print("🔍 Перевірка що старі whitelist-змінні НЕ використовуються")
    print("="*70)
    
    for variable in VARIABLES_TO_CHECK:
        result = search_variable_usage(variable, src_dir)
        results[variable] = result
        
        if result["found"]:
            print(f"\n❌ {variable}: ВИКОРИСТОВУЄТЬСЯ (ПОМИЛКА!)")
            print(f"   Знайдено в файлах ({len(result['files'])}):")
            for file_path in result["files"][:5]:
                relative_path = Path(file_path).relative_to(project_root)
                print(f"   - {relative_path}")
            if len(result["files"]) > 5:
                print(f"   ... та ще {len(result['files']) - 5} файлів")
            used_variables.append(variable)
        else:
            print(f"\n✅ {variable}: НЕ ВИКОРИСТОВУЄТЬСЯ (OK)")
    
    print("\n" + "="*70)
    print("📊 Підсумок")
    print("="*70)
    print(f"Всього перевірено змінних: {len(VARIABLES_TO_CHECK)}")
    print(f"НЕ використовується (OK): {len(VARIABLES_TO_CHECK) - len(used_variables)}")
    print(f"Використовується (ПОМИЛКА): {len(used_variables)}")
    
    if used_variables:
        print("\n❌ ПОМИЛКА: Ці змінні ще використовуються в коді:")
        for var in used_variables:
            print(f"   - {var}")
        print("\n⚠️  Замініть їх на whitelist_config.json + WhitelistManager")
        
        # Тест падає якщо є використовувані змінні
        assert len(used_variables) == 0, (
            f"\n❌ Знайдено {len(used_variables)} старих whitelist-змінних у коді: {used_variables}\n"
            f"Замініть їх на whitelist_config.json + WhitelistManager."
        )
    else:
        print("\n✅ Відмінно! Всі старі whitelist-змінні успішно видалені з коду!")
        print("✅ Проект використовує тільки новий механізм: whitelist_config.json + WhitelistManager")
    
    print("="*70 + "\n")


def test_generate_removal_commands():
    """
    DEPRECATED: Цей тест більше не потрібен.
    Старі whitelist-змінні вже видалені.
    """
    pass


if __name__ == "__main__":
    # Запуск тесту напряму
    test_env_variable_usage()
