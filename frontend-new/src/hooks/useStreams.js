import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

export function useStreams(pollingInterval = 5000) {
  const [streams, setStreams] = useState({});
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchStreamStatus = useCallback(async () => {
    try {
      const response = await api.streams.getAllStatus();
      const streamsData = response.streams || {};

      setStreams(streamsData);

      // Map camera IDs to online status
      const statusMap = {};
      if (streamsData.streams) {
        // streamsData.streams pode ser objeto ou array
        const streamsArray = Array.isArray(streamsData.streams)
          ? streamsData.streams
          : Object.values(streamsData.streams);

        streamsArray.forEach(stream => {
          statusMap[stream.camera_id] = stream.is_healthy ? 'online' : 'offline';
        });
      }
      return statusMap;
    } catch (err) {
      console.error('Error fetching stream status:', err);
      return {};
    }
  }, []);

  const fetchHealth = useCallback(async () => {
    try {
      const response = await api.streams.getHealthReport();
      setHealth(response);
      return response;
    } catch (err) {
      console.error('Error fetching stream health:', err);
      return null;
    }
  }, []);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await fetchStreamStatus();
      await fetchHealth();
      setLoading(false);
    };

    load();

    const interval = setInterval(() => {
      fetchStreamStatus();
      fetchHealth();
    }, pollingInterval);

    return () => clearInterval(interval);
  }, [fetchStreamStatus, fetchHealth, pollingInterval]);

  const getCameraStatus = useCallback((cameraId) => {
    const stream = streams[cameraId];
    if (!stream) return 'unknown';
    return stream.is_healthy ? 'online' : 'offline';
  }, [streams]);

  const startStream = useCallback(async (cameraId) => {
    try {
      const response = await api.cameras.startStream(cameraId);
      await fetchStreamStatus();
      return { success: true, ...response };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }, [fetchStreamStatus]);

  const stopStream = useCallback(async (cameraId) => {
    try {
      const response = await api.cameras.stopStream(cameraId);
      await fetchStreamStatus();
      return { success: true, ...response };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }, [fetchStreamStatus]);

  return {
    streams,
    health,
    loading,
    getCameraStatus,
    startStream,
    stopStream,
    fetchStreamStatus,
  };
}
