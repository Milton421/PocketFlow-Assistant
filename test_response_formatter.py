import unittest
from nodes.response_formatter_node import ResponseFormatter

class TestResponseFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = ResponseFormatter()
        
    def test_unified_teacher_student_resources(self):
        """Test unified format for teacher and student resources"""
        text = """
        Los recursos didácticos son los siguientes:
        Para el profesor: guía didáctica, presentación en PowerPoint, solucionario.
        Para los alumnos: actividades interactivas, cuestionario de autoevaluación, material complementario.
        Para el trabajo en el aula: dinámicas grupales, estudio de casos, debate guiado.
        """
        
        expected = """Los recursos didácticos mencionados en el contexto son los siguientes:

- **Para el profesor:** guía didáctica, presentación en PowerPoint, solucionario
- **Para los alumnos:** actividades interactivas, cuestionario de autoevaluación, material complementario
- **Para el trabajo en el aula:** dinámicas grupales, estudio de casos, debate guiado

Estos recursos se consideran relevantes para el proceso de enseñanza-aprendizaje."""
        
        result = self.formatter.format(text, is_unified_request=True)
        self.assertEqual(result.strip(), expected.strip())
        
    def test_separate_teacher_student_resources(self):
        """Test separate format for teacher and student resources"""
        text = """
        Los recursos didácticos son los siguientes:
        Para el profesor: guía didáctica, presentación en PowerPoint, solucionario.
        Para los alumnos: actividades interactivas, cuestionario de autoevaluación, material complementario.
        """
        
        expected = """**Para el profesor:** guía didáctica, presentación en PowerPoint, solucionario.
**Para los alumnos:** actividades interactivas, cuestionario de autoevaluación, material complementario."""
        
        result = self.formatter.format(text, is_unified_request=False)
        self.assertEqual(result.strip(), expected.strip())
        
    def test_mixed_content_formatting(self):
        """Test mixed content with narrative and list items"""
        text = """
        El documento menciona varios aspectos importantes. Por un lado, se destacan los siguientes elementos: 
        análisis de texto, comprensión lectora, expresión escrita. 
        Por otro lado, también se mencionan actividades prácticas como: ejercicios de vocabulario, 
        redacción de ensayos y debates en grupo.
        """
        
        # Should use simple list format for unified request
        unified_result = self.formatter.format(text, is_unified_request=True)
        self.assertIn("•", unified_result)  # Should contain bullet points
        
        # Should use narrative format for separate request
        separate_result = self.formatter.format(text, is_unified_request=False)
        self.assertNotIn("•", separate_result)  # Should not contain bullet points
        
    def test_simple_list_formatting(self):
        """Test simple list formatting"""
        text = "Los recursos incluyen: libro de texto, cuaderno de ejercicios, material multimedia"
        
        # Unified request should use bullet points
        unified_result = self.formatter.format(text, is_unified_request=True)
        self.assertIn("•", unified_result)
        
        # Separate request should use narrative format
        separate_result = self.formatter.format(text, is_unified_request=False)
        self.assertNotIn("•", separate_result)
        self.assertIn("libro de texto, cuaderno de ejercicios, material multimedia", separate_result)

if __name__ == "__main__":
    unittest.main()
