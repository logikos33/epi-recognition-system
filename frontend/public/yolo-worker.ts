// frontend/public/yolo-worker.ts
/**
 * Web Worker for YOLO data polling
 * Runs in separate thread - doesn't block UI
 */

interface PollingRequest {
  type: 'poll'
  cameraIds: number[]
  apiBase: string
  token: string | null
  interval: number
}

interface WorkerResponse {
  type: 'poll'
  data: Map<number, YOLOCameraData>
  timestamp: number
}

interface YOLOCameraData {
  session_id: string
  camera_id: number
  license_plate: string | null
  truck_entry_time: string
  products_counted: Record<string, number> | null
  item_count: number
  elapsed_time_formatted: string
  elapsed_seconds: number
  status: 'active' | 'completed' | 'paused'
}

/**
 * Calculate elapsed time from entry time
 */
function calculateElapsedTime(entryTime: string): { formatted: string; seconds: number } {
  const now = new Date()
  const entry = new Date(entryTime)
  const elapsedMs = now.getTime() - entry.getTime()
  const elapsedSeconds = Math.floor(elapsedMs / 1000)

  const hours = Math.floor(elapsedSeconds / 3600)
  const minutes = Math.floor((elapsedSeconds % 3600) / 60)
  const seconds = elapsedSeconds % 60

  if (hours > 0) {
    return {
      formatted: `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`,
      seconds: elapsedSeconds
    }
  }

  return {
    formatted: `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`,
    seconds: elapsedSeconds
  }
}

/**
 * Fetch YOLO data for cameras via batch query
 */
async function fetchYOLOData(
  cameraIds: number[],
  apiBase: string,
  token: string | null
): Promise<Map<number, YOLOCameraData>> {
  const resultMap = new Map<number, YOLOCameraData>()

  try {
    // Build headers - only add Authorization if token exists
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    // Batch query - fetch all cameras at once instead of individual requests
    // Backend expects comma-separated camera_ids parameter
    const cameraIdsParam = cameraIds.join(',')
    const response = await fetch(
      `${apiBase}/api/sessions/batch?camera_ids=${cameraIdsParam}&status=active`,
      {
        method: 'GET',
        headers
      }
    )

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const data = await response.json()

    if (data.success && data.sessions) {
      // Process each session
      data.sessions.forEach((session: any) => {
        const productsCounted = session.products_counted || {}
        const itemCount = Object.values(productsCounted).reduce((sum: number, count: any) => sum + (count || 0), 0)

        const elapsedInfo = calculateElapsedTime(session.truck_entry_time)

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
        })
      })
    }
  } catch (error) {
    console.error('[YOLO Worker] Error fetching data:', error)
  }

  return resultMap
}

/**
 * Main polling loop
 */
let pollingInterval: ReturnType<typeof setInterval> | null = null

self.onmessage = async (event: MessageEvent<PollingRequest>) => {
  const { type, cameraIds, apiBase, token, interval } = event.data

  if (type !== 'poll') {
    return
  }

  // Clear existing interval if any
  if (pollingInterval) {
    clearInterval(pollingInterval)
  }

  // Initial fetch
  let data = await fetchYOLOData(cameraIds, apiBase, token)

  // Send initial data
  const response: WorkerResponse = {
    type: 'poll',
    data,
    timestamp: Date.now()
  }
  self.postMessage(response)

  // Start polling loop
  pollingInterval = setInterval(async () => {
    data = await fetchYOLOData(cameraIds, apiBase, token)

    const response: WorkerResponse = {
      type: 'poll',
      data,
      timestamp: Date.now()
    }
    self.postMessage(response)
  }, interval)
}

// Handle cleanup
self.onmessage = (event: MessageEvent) => {
  if (event.data.type === 'cleanup') {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
    }
  }
}

export {}
