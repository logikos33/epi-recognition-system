export interface YOLOClass {
  id: string;
  name: string;
  displayName: string;
  color: string;
  confidenceThreshold: number;
  isActive: boolean;
  createdAt: string;
}

export interface TrainingJob {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  epochs?: number;
  currentEpoch?: number;
  datasetSize: number;
  model: string;
  startedAt: string;
  completedAt?: string;
  metrics?: {
    mAP50?: number;
    mAP95?: number;
    precision?: number;
    recall?: number;
  };
}
