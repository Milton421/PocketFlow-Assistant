from nodes.response_formatter_node import ResponseFormatter

def run_tests():
    formatter = ResponseFormatter()
    
    # Test 1: Unified format (bulleted lists)
    print("\n=== TEST 1: UNIFIED FORMAT ===")
    unified_text = """
    Para el profesor: guía didáctica, presentación en PowerPoint, solucionario.
    Para los alumnos: actividades interactivas, cuestionario de autoevaluación.
    """
    print("Input:")
    print(unified_text)
    print("Output:")
    print(formatter.format(unified_text, is_unified_request=True))
    
    # Test 2: Separate format (comma-separated)
    print("\n=== TEST 2: SEPARATE FORMAT ===")
    separate_text = """
    Para el profesor: guía didáctica, presentación en PowerPoint.
    Para los alumnos: actividades interactivas, cuestionario.
    """
    print("Input:")
    print(separate_text)
    print("Output:")
    print(formatter.format(separate_text, is_unified_request=False))
    
    # Test 3: Edge case - empty input
    print("\n=== TEST 3: EMPTY INPUT ===")
    print("Input: ''")
    print("Output:", formatter.format(""))

if __name__ == "__main__":
    print("=== SIMPLE TEST SCRIPT FOR RESPONSE FORMATTER ===")
    run_tests()
    print("\n=== TEST COMPLETED ===")
