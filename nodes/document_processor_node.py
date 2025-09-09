from utils.document_processor import DocumentProcessor

class DocumentProcessorNode:
    def process(self, file_path, metadata):
        processor = DocumentProcessor()
        return processor.process(file_path, metadata)
    