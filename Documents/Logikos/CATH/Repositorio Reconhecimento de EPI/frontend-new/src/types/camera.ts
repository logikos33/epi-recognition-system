export interface Camera {
  id: string;
  name: string;
  ipAddress: string;
  port: number;
  username?: string;
  password?: string;
  rtspPath?: string;
  model: string;
  location?: string;
  status: 'online' | 'offline' | 'error';
  isActive: boolean;
  createdAt: string;
}

export interface CameraFormData {
  name: string;
  ipAddress: string;
  port: number;
  username?: string;
  password?: string;
  rtspPath?: string;
  model: string;
  location?: string;
}
