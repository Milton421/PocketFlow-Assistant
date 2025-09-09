from nodes.response_formatter_node import ResponseFormatter

def test_unified_format():
    """Test the unified format output (bulleted lists)"""
    print("\n=== TEST: UNIFIED FORMAT (BULLETED LISTS) ===")
    
    formatter = ResponseFormatter()
    
    test_cases = [
        {
            "name": "Teacher and student resources",
            "input": """
            Para el profesor: guía didáctica, presentación en PowerPoint, solucionario.
            Para los alumnos: actividades interactivas, cuestionario de autoevaluación.
            """,
            "expected": [
                "Para el profesor:",
                "guía didáctica, presentación en PowerPoint, solucionario",
                "Para los alumnos:",
                "actividades interactivas, cuestionario de autoevaluación"
            ]
        },
        {
            "name": "Classroom activities",
            "input": """
            Para el trabajo en el aula: dinámicas grupales, estudio de casos, debate guiado.
            """,
            "expected": [
                "Para el trabajo en el aula:",
                "dinámicas grupales, estudio de casos, debate guiado"
            ]
        }
    ]
    
    for case in test_cases:
        print(f"\n--- Testing: {case['name']} ---")
        print("Input:")
        print(case['input'].strip())
        
        result = formatter.format(case['input'], is_unified_request=True)
        print("\nOutput:")
        print(result)
        
        # Verify all expected strings are in the result
        for expected_str in case['expected']:
            assert expected_str in result, f"Expected string not found: {expected_str}"
        
        print("✅ Test passed!")

def test_separate_format():
    """Test the separate format output (comma-separated paragraphs)"""
    print("\n=== TEST: SEPARATE FORMAT (COMMA-SEPARATED) ===")
    
    formatter = ResponseFormatter()
    
    test_cases = [
        {
            "name": "Teacher resources only",
            "input": "Para el profesor: guía didáctica, presentación en PowerPoint.",
            "expected": "**Para el profesor:** guía didáctica, presentación en PowerPoint."
        },
        {
            "name": "Student resources with extra text",
            "input": "Algunos recursos para los alumnos son: actividades interactivas, cuestionario.",
            "expected": "actividades interactivas, cuestionario"
        },
        {
            "name": "Multiple sections",
            "input": """
            Para el profesor: guía didáctica, presentación.
            Para los alumnos: actividades, cuestionario.
            """,
            "expected_teacher": "**Para el profesor:** guía didáctica, presentación.",
            "expected_student": "**Para los alumnos:** actividades, cuestionario."
        }
    ]
    
    for case in test_cases:
        print(f"\n--- Testing: {case['name']} ---")
        print("Input:")
        print(case['input'].strip())
        
        result = formatter.format(case['input'], is_unified_request=False)
        print("\nOutput:")
        print(result)
        
        # Verify expected strings
        if 'expected' in case:
            assert case['expected'] in result, f"Expected string not found: {case['expected']}"
        if 'expected_teacher' in case:
            assert case['expected_teacher'] in result, f"Teacher section not found"
        if 'expected_student' in case:
            assert case['expected_student'] in result, f"Student section not found"
            
        print("✅ Test passed!")

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n=== TEST: EDGE CASES ===")
    
    formatter = ResponseFormatter()
    
    # Empty input
    assert formatter.format("") == "No se encontró información suficiente"
    
    # No sections found
    no_sections = "Este es un texto sin secciones específicas."
    assert formatter.format(no_sections, is_unified_request=True) == formatter.format(no_sections, is_unified_request=False)
    
    print("✅ All edge case tests passed!")

if __name__ == "__main__":
    print("=== INICIANDO PRUEBAS DEL FORMATEADOR ===")
    test_unified_format()
    test_separate_format()
    test_edge_cases()
    print("\n=== TODAS LAS PRUEBAS COMPLETADAS CON ÉXITO ===")
