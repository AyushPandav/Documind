import { useApp } from '@/context/AppContext';

export function useDocuments() {
  const {
    documents,
    selectedDocument,
    setSelectedDocument,
    isUploading,
    uploadProgress,
    uploadingDocName,
    pickAndUploadDocument,
  } = useApp();

  return {
    documents,
    selectedDocument,
    setSelectedDocument,
    isUploading,
    uploadProgress,
    uploadingDocName,
    uploadDocument: pickAndUploadDocument,
  };
}
