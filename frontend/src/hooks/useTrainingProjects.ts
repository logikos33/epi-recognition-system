'use client'

import { useQuery, useMutation, useQueryClient, type UseQueryResult } from '@tanstack/react-query'
import {
  listTrainingProjects,
  getTrainingProject,
  createTrainingProject,
  updateTrainingProject,
  deleteTrainingProject,
  updateTrainingProjectStatus,
} from '@/lib/api'
import type {
  TrainingProject,
  CreateTrainingProjectRequest,
  UpdateTrainingProjectRequest,
  TrainingProjectStatus,
} from '@/types/training'

/**
 * Query key factory for training projects
 */
const trainingProjectKeys = {
  all: ['training-projects'] as const,
  lists: () => [...trainingProjectKeys.all, 'list'] as const,
  list: () => [...trainingProjectKeys.lists()] as const,
  details: () => [...trainingProjectKeys.all, 'detail'] as const,
  detail: (id: string) => [...trainingProjectKeys.details(), id] as const,
}

/**
 * Hook to fetch all training projects for the current user
 *
 * @returns React Query result with projects array
 *
 * @example
 * const { data: projects, isLoading, error } = useTrainingProjects()
 */
export function useTrainingProjects(): UseQueryResult<TrainingProject[], Error> {
  return useQuery({
    queryKey: trainingProjectKeys.list(),
    queryFn: async () => {
      const response = await listTrainingProjects()
      if (!response.success) {
        throw new Error(response.error || 'Failed to fetch training projects')
      }
      return response.projects || []
    },
  })
}

/**
 * Hook to fetch a single training project by ID
 *
 * @param id - Project ID to fetch
 * @returns React Query result with project data
 *
 * @example
 * const { data: project, isLoading, error } = useTrainingProject('uuid')
 */
export function useTrainingProject(id: string): UseQueryResult<TrainingProject, Error> {
  return useQuery({
    queryKey: trainingProjectKeys.detail(id),
    queryFn: async () => {
      const response = await getTrainingProject(id)
      if (!response.success) {
        throw new Error(response.error || 'Failed to fetch training project')
      }
      return response.project
    },
    enabled: !!id, // Only run query if ID is provided
  })
}

/**
 * Hook to create a new training project
 *
 * @returns Mutation object with trigger function
 *
 * @example
 * const createProject = useCreateTrainingProject()
 * createProject.mutate(
 *   { name: 'My Project', target_classes: ['helmet', 'vest'] },
 *   { onSuccess: () => console.log('Created!') }
 * )
 */
export function useCreateTrainingProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: CreateTrainingProjectRequest) => {
      const response = await createTrainingProject(data)
      if (!response.success) {
        throw new Error(response.error || 'Failed to create training project')
      }
      return response.project
    },
    onSuccess: () => {
      // Invalidate and refetch projects list
      queryClient.invalidateQueries({ queryKey: trainingProjectKeys.list() })
    },
  })
}

/**
 * Hook to update an existing training project
 *
 * @returns Mutation object with trigger function
 *
 * @example
 * const updateProject = useUpdateTrainingProject()
 * updateProject.mutate(
 *   { id: 'uuid', name: 'Updated Name' },
 *   { onSuccess: () => console.log('Updated!') }
 * )
 */
export function useUpdateTrainingProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, ...data }: { id: string } & UpdateTrainingProjectRequest) => {
      const response = await updateTrainingProject(id, data)
      if (!response.success) {
        throw new Error(response.error || 'Failed to update training project')
      }
      return response.project
    },
    onSuccess: (updatedProject, variables) => {
      // Invalidate and refetch projects list
      queryClient.invalidateQueries({ queryKey: trainingProjectKeys.list() })
      // Invalidate specific project detail
      queryClient.invalidateQueries({ queryKey: trainingProjectKeys.detail(variables.id) })
    },
  })
}

/**
 * Hook to delete a training project
 *
 * @returns Mutation object with trigger function
 *
 * @example
 * const deleteProject = useDeleteTrainingProject()
 * deleteProject.mutate('uuid', { onSuccess: () => console.log('Deleted!') })
 */
export function useDeleteTrainingProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await deleteTrainingProject(id)
      if (!response.success) {
        throw new Error(response.error || 'Failed to delete training project')
      }
      return id
    },
    onSuccess: (_, deletedId) => {
      // Invalidate and refetch projects list
      queryClient.invalidateQueries({ queryKey: trainingProjectKeys.list() })
      // Remove specific project detail from cache
      queryClient.removeQueries({ queryKey: trainingProjectKeys.detail(deletedId) })
    },
  })
}

/**
 * Hook to update training project status
 *
 * @returns Mutation object with trigger function
 *
 * @example
 * const updateStatus = useUpdateProjectStatus()
 * updateStatus.mutate(
 *   { id: 'uuid', status: 'training' },
 *   { onSuccess: () => console.log('Status updated!') }
 * )
 */
export function useUpdateProjectStatus() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: TrainingProjectStatus }) => {
      const response = await updateTrainingProjectStatus(id, status)
      if (!response.success) {
        throw new Error(response.error || 'Failed to update project status')
      }
      return response
    },
    onSuccess: (_, variables) => {
      // Invalidate and refetch projects list
      queryClient.invalidateQueries({ queryKey: trainingProjectKeys.list() })
      // Invalidate specific project detail
      queryClient.invalidateQueries({ queryKey: trainingProjectKeys.detail(variables.id) })
    },
  })
}
