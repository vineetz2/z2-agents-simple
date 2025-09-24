import React, { useState } from 'react'
import axios from 'axios'

interface FileUploadProps {
  onFileProcessed: (data: any) => void
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileProcessed }) => {
  const [isUploading, setIsUploading] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<any>(null)
  const [isEnriching, setIsEnriching] = useState(false)

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post('http://localhost:8002/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      setUploadedFile(response.data)
      onFileProcessed(response.data)
      setIsUploading(false)
    } catch (error) {
      console.error('Upload error:', error)
      setIsUploading(false)
      alert('Error uploading file')
    }
  }

  const handleEnrichment = async () => {
    if (!uploadedFile) return

    setIsEnriching(true)
    try {
      const response = await axios.post('http://localhost:8002/api/enrich', {
        file_content: JSON.stringify(uploadedFile.preview),
        enrichment_type: 'auto'
      })

      onFileProcessed(response.data)
      setIsEnriching(false)
      alert(`Successfully enriched ${response.data.rows_enriched} rows`)
    } catch (error) {
      console.error('Enrichment error:', error)
      setIsEnriching(false)
      alert('Error enriching data')
    }
  }

  return (
    <div style={{
      padding: '15px',
      background: '#f0f2f5',
      borderRadius: '8px',
      marginBottom: '20px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
        <label style={{
          padding: '8px 16px',
          background: '#4CAF50',
          color: 'white',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px',
          fontWeight: 500,
          display: 'inline-block'
        }}>
          📁 Upload File
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
            disabled={isUploading}
          />
        </label>

        {uploadedFile && (
          <>
            <span style={{ color: '#666' }}>
              {uploadedFile.filename} ({uploadedFile.rows} rows)
            </span>
            <button
              onClick={handleEnrichment}
              disabled={isEnriching}
              style={{
                padding: '8px 16px',
                background: '#2196F3',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: isEnriching ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                fontWeight: 500
              }}
            >
              {isEnriching ? 'Enriching...' : '🔧 Enrich Data'}
            </button>
          </>
        )}

        {(isUploading || isEnriching) && (
          <span style={{ color: '#666' }}>Processing...</span>
        )}
      </div>

      {uploadedFile && uploadedFile.columns && (
        <div style={{ marginTop: '10px', fontSize: '12px', color: '#666' }}>
          Columns: {uploadedFile.columns.join(', ')}
        </div>
      )}
    </div>
  )
}

export default FileUpload