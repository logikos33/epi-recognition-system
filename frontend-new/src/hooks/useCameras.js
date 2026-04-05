import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

export function useCameras() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch all cameras
  const fetchCameras = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.cameras.list();
      setCameras(data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching cameras:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Create camera
  const createCamera = useCallback(async (cameraData) => {
    try {
      const newCamera = await api.cameras.create(cameraData);
      setCameras(prev => [...prev, newCamera]);
      return { success: true, camera: newCamera };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }, []);

  // Update camera
  const updateCamera = useCallback(async (cameraId, cameraData) => {
    try {
      const updatedCamera = await api.cameras.update(cameraId, cameraData);
      setCameras(prev =>
        prev.map(cam => cam.id === cameraId ? updatedCamera : cam)
      );
      return { success: true, camera: updatedCamera };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }, []);

  // Delete camera
  const deleteCamera = useCallback(async (cameraId) => {
    try {
      await api.cameras.delete(cameraId);
      setCameras(prev => prev.filter(cam => cam.id !== cameraId));
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }, []);

  // Test camera connection
  const testConnection = useCallback(async (ip, port, username, password) => {
    try {
      const result = await api.cameras.testConnection(ip, port, username, password);
      return { success: true, ...result };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchCameras();
  }, [fetchCameras]);

  return {
    cameras,
    loading,
    error,
    refetch: fetchCameras,
    createCamera,
    updateCamera,
    deleteCamera,
    testConnection,
  };
}
