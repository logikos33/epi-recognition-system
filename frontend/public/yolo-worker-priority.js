function calculateElapsedTime(entryTime) {
  const now = /* @__PURE__ */ new Date();
  const entry = new Date(entryTime);
  const elapsedMs = now.getTime() - entry.getTime();
  const elapsedSeconds = Math.floor(elapsedMs / 1e3);
  const hours = Math.floor(elapsedSeconds / 3600);
  const minutes = Math.floor(elapsedSeconds % 3600 / 60);
  const seconds = elapsedSeconds % 60;
  if (hours > 0) {
    return {
      formatted: `${hours}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`,
      seconds: elapsedSeconds
    };
  }
  return {
    formatted: `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`,
    seconds: elapsedSeconds
  };
}
async function fetchYOLOData(cameraIds, apiBase, token) {
  const resultMap = /* @__PURE__ */ new Map();
  try {
    const headers = {
      "Content-Type": "application/json"
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    const cameraIdsParam = cameraIds.join(",");
    const response = await fetch(
      `${apiBase}/api/sessions/batch?camera_ids=${cameraIdsParam}&status=active`,
      {
        method: "GET",
        headers
      }
    );
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
    if (data.success && data.sessions) {
      data.sessions.forEach((session) => {
        const productsCounted = session.products_counted || {};
        const itemCount = Object.values(productsCounted).reduce((sum, count) => sum + (count || 0), 0);
        const elapsedInfo = calculateElapsedTime(session.truck_entry_time);
        resultMap.set(session.camera_id, {
          session_id: session.id,
          camera_id: session.camera_id,
          license_plate: session.license_plate,
          truck_entry_time: session.truck_entry_time,
          products_counted: productsCounted,
          item_count: itemCount,
          elapsed_time_formatted: elapsedInfo.formatted,
          elapsed_seconds: elapsedInfo.seconds,
          status: session.status
        });
      });
    }
  } catch (error) {
    console.error(`[YOLO Worker Priority] Error fetching data:`, error);
  }
  return resultMap;
}
const activeIntervals = /* @__PURE__ */ new Map();
self.onmessage = async (event) => {
  const message = event.data;
  if (message.type === "cleanup") {
    activeIntervals.forEach((interval) => clearInterval(interval));
    activeIntervals.clear();
    return;
  }
  if (message.type === "poll") {
    const { type, priority, cameraIds, apiBase, token, interval } = message;
    const existingInterval = activeIntervals.get(priority);
    if (existingInterval) {
      clearInterval(existingInterval);
    }
    let data = await fetchYOLOData(cameraIds, apiBase, token);
    const response = {
      type: "poll",
      priority,
      data,
      timestamp: Date.now()
    };
    self.postMessage(response);
    const pollingInterval = setInterval(async () => {
      data = await fetchYOLOData(cameraIds, apiBase, token);
      const response2 = {
        type: "poll",
        priority,
        data,
        timestamp: Date.now()
      };
      self.postMessage(response2);
    }, interval);
    activeIntervals.set(priority, pollingInterval);
  }
};
