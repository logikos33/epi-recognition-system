import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

interface TrainingProject {
  id: string
  name: string
  description: string
  status: 'preparing' | 'training' | 'completed' | 'failed'
  classes_count: number
  images_count: number
  created_at: string
  updated_at: string
}

interface CreateProjectData {
  name: string
  description?: string
}

export function useTrainingProjects() {
  const queryClient = useQueryClient()

  const projects = useQuery({
    queryKey: ['training-projects'],
    queryFn: async () => {
      const response = await api.get<{ projects: TrainingProject[] }>('/api/training/projects')
      return response.projects
    }
  })

  const createProject = useMutation({
    mutationFn: async (data: CreateProjectData) => {
      const response = await api.post<{ project: TrainingProject }>('/api/training/projects', data)
      return response.project
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training-projects'] })
    }
  })

  const deleteProject = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/training/projects/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training-projects'] })
    }
  })

  return {
    projects: projects.data || [],
    isLoading: projects.isLoading,
    error: projects.error,
    createProject: createProject.mutateAsync,
    deleteProject: deleteProject.mutateAsync,
    isCreating: createProject.isPending,
    isDeleting: deleteProject.isPending
  }
}
