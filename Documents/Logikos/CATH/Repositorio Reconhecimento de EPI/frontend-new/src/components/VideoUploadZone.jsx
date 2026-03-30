import { useState } from 'react'

export default function VideoUploadZone({ onUploadComplete }) {
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleUpload(e.dataTransfer.files[0])
    }
  }

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleUpload(e.target.files[0])
    }
  }

  const handleUpload = async (file) => {
    // Validate file type
    const validTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/mkv']
    if (!validTypes.includes(file.type)) {
      alert('Por favor, selecione um arquivo de vídeo válido (MP4, AVI, MOV, MKV)')
      return
    }

    setUploading(true)
    setProgress(0)

    const formData = new FormData()
    formData.append('video', file)

    try {
      const token = localStorage.getItem('token')

      // Simulate progress (real progress would require upload tracking)
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return 90
          }
          return prev + 10
        })
      }, 200)

      const response = await fetch('/api/training/videos/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      clearInterval(progressInterval)
      setProgress(100)

      const result = await response.json()

      if (result.success) {
        setUploading(false)
        setProgress(0)
        if (onUploadComplete) {
          onUploadComplete(result)
        }
      } else {
        alert('Erro no upload: ' + result.error)
        setUploading(false)
        setProgress(0)
      }

    } catch (error) {
      alert('Erro no upload: ' + error.message)
      setUploading(false)
      setProgress(0)
    }
  }

  return (
    <div
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      style={{
        border: `2px dashed ${dragActive ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: '14px',
        padding: '60px 20px',
        textAlign: 'center',
        background: dragActive ? 'rgba(37,99,235,0.05)' : 'var(--card)',
        cursor: 'pointer',
        transition: 'all 0.15s'
      }}
      onClick={() => !uploading && document.getElementById('video-upload-input').click()}
    >
      <input
        id="video-upload-input"
        type="file"
        accept="video/mp4,video/avi,video/mov,video/mkv"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
        disabled={uploading}
      />

      {uploading ? (
        <div>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
          <p style={{ fontSize: '14px', color: 'var(--muted)', marginBottom: '12px' }}>
            Enviando vídeo...
          </p>
          <div style={{
            width: '200px',
            height: '4px',
            background: 'var(--border)',
            borderRadius: '2px',
            margin: '0 auto',
            overflow: 'hidden'
          }}>
            <div style={{
              width: `${progress}%`,
              height: '100%',
              background: 'var(--accent)',
              transition: 'width 0.3s'
            }} />
          </div>
          <p style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '8px' }}>
            {progress}%
          </p>
        </div>
      ) : (
        <div>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📁</div>
          <p style={{ fontSize: '16px', fontWeight: '500', marginBottom: '8px' }}>
            Arraste e solte o vídeo aqui
          </p>
          <p style={{ fontSize: '14px', color: 'var(--muted)', marginBottom: '16px' }}>
            ou clique para selecionar
          </p>
          <p style={{ fontSize: '12px', color: 'var(--muted)' }}>
            MP4, AVI, MOV, MKV (máx 500MB)
          </p>
        </div>
      )}
    </div>
  )
}
