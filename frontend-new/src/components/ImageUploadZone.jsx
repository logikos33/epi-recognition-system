import { useState, useRef } from 'react';

export default function ImageUploadZone({ onUploadComplete, onClose }) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const validateFile = (file) => {
    // Check file type
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    if (!validTypes.includes(file.type)) {
      setError('Formato inválido. Use JPG ou PNG.');
      return false;
    }

    // Check file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      setError('Arquivo muito grande. Máximo 10MB por imagem.');
      return false;
    }

    return true;
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = (files) => {
    setError(null);

    // Convert to array and validate
    const fileArray = Array.from(files);

    if (fileArray.length > 100) {
      setError('Máximo 100 imagens por upload.');
      return;
    }

    // Validate each file
    const validFiles = fileArray.filter(file => {
      if (!validateFile(file)) {
        return false;
      }
      return true;
    });

    if (validFiles.length === 0) {
      return;
    }

    // Add to selected files (avoiding duplicates)
    const newFiles = [...selectedFiles];
    for (const file of validFiles) {
      if (!newFiles.some(f => f.name === file.name && f.size === file.size)) {
        newFiles.push(file);
      }
    }

    if (newFiles.length > 100) {
      setError('Máximo 100 imagens por upload.');
      return;
    }

    setSelectedFiles(newFiles);
  };

  const removeFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setError('Selecione pelo menos uma imagem.');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();

      // Append all files with 'images' key
      selectedFiles.forEach(file => {
        formData.append('images', file);
      });

      const xhr = new XMLHttpRequest();

      // Track upload progress
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = (e.loaded / e.total) * 100;
          setUploadProgress(percentComplete);
        }
      });

      // Handle completion
      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          const response = JSON.parse(xhr.responseText);
          if (response.success) {
            setUploading(false);
            setUploadProgress(100);
            setSelectedFiles([]);
            if (onUploadComplete) {
              onUploadComplete(response);
            }
            // Auto-close after successful upload
            setTimeout(() => {
              if (onClose) onClose();
            }, 1000);
          } else {
            setUploading(false);
            setError(response.error || 'Erro no upload');
          }
        } else {
          setUploading(false);
          setError('Erro no upload. Tente novamente.');
        }
      });

      // Handle error
      xhr.addEventListener('error', () => {
        setUploading(false);
        setError('Erro de conexão. Tente novamente.');
      });

      // Send request
      xhr.open('POST', '/api/training/images/upload');
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.send(formData);

    } catch (err) {
      setUploading(false);
      setError('Erro no upload: ' + err.message);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Upload Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current.click()}
        style={{
          border: `2px dashed ${dragActive ? 'var(--accent)' : 'var(--border)'}`,
          borderRadius: '12px',
          padding: '40px',
          textAlign: 'center',
          cursor: uploading ? 'not-allowed' : 'pointer',
          background: dragActive ? 'var(--accent5)' : 'var(--bg)',
          transition: 'all 0.2s',
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/jpeg,image/jpg,image/png"
          onChange={handleChange}
          disabled={uploading}
          style={{ display: 'none' }}
        />

        {uploading ? (
          <div>
            <div style={{ fontSize: '48px', marginBottom: '12px' }}>⏳</div>
            <div style={{ fontSize: '14px', color: 'var(--muted)', marginBottom: '8px' }}>
              Enviando imagens...
            </div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--accent)' }}>
              {Math.round(uploadProgress)}%
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: '48px', marginBottom: '12px' }}>📁</div>
            <div style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text)', marginBottom: '8px' }}>
              Arraste imagens aqui
            </div>
            <div style={{ fontSize: '14px', color: 'var(--muted)', marginBottom: '16px' }}>
              ou clique para selecionar
            </div>
            <div style={{ fontSize: '12px', color: 'var(--muted)' }}>
              JPG, PNG • Máx 10MB cada • Máx 100 imagens
            </div>
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div style={{
          padding: '12px',
          borderRadius: '8px',
          background: '#ef444410',
          border: '1px solid #ef444440',
          color: '#ef4444',
          fontSize: '14px',
        }}>
          {error}
        </div>
      )}

      {/* Selected Files */}
      {selectedFiles.length > 0 && (
        <div>
          <div style={{
            fontSize: '14px',
            fontWeight: '600',
            color: 'var(--text)',
            marginBottom: '12px',
          }}>
            {selectedFiles.length} imagem{selectedFiles.length !== 1 ? 's' : ''} selecionada{selectedFiles.length !== 1 ? 's' : ''}
          </div>

          <div style={{
            maxHeight: '200px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}>
            {selectedFiles.map((file, index) => (
              <div
                key={index}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                }}
              >
                <div style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '6px',
                  background: 'var(--card)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '20px',
                }}>
                  🖼️
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: '14px',
                    fontWeight: '500',
                    color: 'var(--text)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {file.name}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--muted)' }}>
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(index);
                  }}
                  disabled={uploading}
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '6px',
                    background: uploading ? 'var(--bg)' : '#ef444410',
                    border: '1px solid #ef444440',
                    color: '#ef4444',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: uploading ? 'not-allowed' : 'pointer',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={(e) => {
                    if (!uploading) {
                      e.currentTarget.style.background = '#ef4444';
                      e.currentTarget.style.color = '#fff';
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = '#ef444410';
                    e.currentTarget.style.color = '#ef4444';
                  }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M18 6L6 18M6 6l12 12"/>
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      {selectedFiles.length > 0 && (
        <div style={{
          display: 'flex',
          gap: '12px',
          justifyContent: 'flex-end',
          paddingTop: '12px',
          borderTop: '1px solid var(--border)',
        }}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setSelectedFiles([]);
              setError(null);
            }}
            disabled={uploading}
            style={{
              padding: '10px 20px',
              borderRadius: '8px',
              background: 'var(--bg)',
              border: '1px solid var(--border)',
              color: 'var(--text)',
              fontSize: '14px',
              fontWeight: '600',
              cursor: uploading ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s',
            }}
          >
            Limpar
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              handleUpload();
            }}
            disabled={uploading}
            style={{
              padding: '10px 20px',
              borderRadius: '8px',
              background: uploading ? 'var(--muted)' : 'var(--accent)',
              border: 'none',
              color: '#fff',
              fontSize: '14px',
              fontWeight: '600',
              cursor: uploading ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {uploading ? 'Enviando...' : `Enviar ${selectedFiles.length} imagem${selectedFiles.length !== 1 ? 's' : ''}`}
          </button>
        </div>
      )}
    </div>
  );
}
